#!/usr/bin/env python3
"""ga-codex.py - GA→Codex bridge CLI.

Wraps `codex exec` (via WSL) with real-time progress feedback.
Usage:
    ga-codex.py [--progress] [--session ID] [--workdir PATH] [--role ROLE] [--timeout SEC] [--model MODEL] "prompt"
    ga-codex.py [--progress] [--session ID] [--workdir PATH] [--role ROLE] --file PROMPT_FILE

Examples:
    # Simple task
    ga-codex.py "list all TODO comments in the codebase"

    # With progress + role + session resume
    ga-codex.py --progress --role architect --session abc123 --workdir /home/user/project "design auth API"

    # Read prompt from file
    ga-codex.py --progress --file plan.md

Output:
    stdout: final result (last message from codex)
    stderr: progress events (when --progress)
    exit code: 0 on success, 1 on error
"""

import argparse
import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Optional


# --- Config ---

SCRIPT_DIR = Path(__file__).resolve().parent
ROLES_DIR = SCRIPT_DIR / "codex-bridge" / "roles"
SESSIONS_FILE = SCRIPT_DIR / "codex-bridge" / "sessions.json"
WSL_DISTRO = "Ubuntu_01_25"
DEFAULT_MODEL = "gpt-5.4"
DEFAULT_TIMEOUT = 600  # 10 minutes


# --- Progress display helpers ---

def progress_msg(msg: str, icon: str = "·") -> None:
    """Print a progress message to stderr."""
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] {icon} {msg}", file=sys.stderr, flush=True)


def progress_step(step: str) -> None:
    progress_msg(step, "▶")


def progress_done(msg: str) -> None:
    progress_msg(msg, "✅")


def progress_warn(msg: str) -> None:
    progress_msg(msg, "⚠️")


def progress_error(msg: str) -> None:
    progress_msg(msg, "❌")


# --- Async status file writer ---

def _write_async_status(path: Path, status: str, progress: str = "",
                        result: str = "", thread_id: str = "") -> None:
    """Write async status JSON for GA to poll."""
    data = {
        "status": status,       # running | done | error
        "progress": progress,
        "result": result,
        "thread_id": thread_id,
        "updated": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


# --- JSONL event parser ---

def parse_event(line: str) -> Optional[dict]:
    """Parse a single JSONL line into an event dict."""
    line = line.strip()
    if not line:
        return None
    try:
        return json.loads(line)
    except json.JSONDecodeError:
        return None


def describe_event(event: dict) -> Optional[str]:
    """Convert a JSONL event to a human-readable progress description."""
    etype = event.get("type", "")

    if etype == "thread.started":
        tid = event.get("thread_id", "?")
        return f"Session started: {tid[:12]}..."

    elif etype == "turn.started":
        return "Thinking..."

    elif etype == "turn.completed":
        return "Turn completed"

    elif etype == "turn.failed":
        err = event.get("error", {})
        msg = err.get("message", "unknown error") if isinstance(err, dict) else str(err)
        return f"Turn failed: {msg}"

    elif etype == "error":
        msg = event.get("message", "unknown error")
        return f"Error: {msg}"

    elif etype == "message.delta":
        # Content streaming delta - show what tool is being called
        content = event.get("content", {})
        if isinstance(content, dict):
            # Tool call
            name = content.get("name", "")
            if name:
                return f"Tool: {name}"
            # Text delta - skip (too verbose)
        return None

    elif etype == "item.started":
        item = event.get("item", {})
        itype = item.get("type", "")
        if itype == "command_execution":
            cmd = item.get("command", "")
            preview = cmd.split("-lc")[-1][:60].strip() if "-lc" in cmd else cmd[:60]
            return f"Running: {preview}"
        elif itype == "function_call":
            name = item.get("name", "")
            return f"Calling: {name}"
        elif itype == "message":
            role = item.get("role", "")
            return f"Generating response ({role})..."
        return None

    elif etype == "item.completed":
        item = event.get("item", {})
        itype = item.get("type", "")
        if itype == "agent_message":
            text = item.get("text", "")
            preview = text[:60].replace("\n", " ") if text else ""
            return f"Reply: {preview}..."
        elif itype == "command_execution":
            cmd = item.get("command", "")
            exit_code = item.get("exit_code", "?")
            preview = cmd.split("-lc")[-1][:50].strip() if "-lc" in cmd else cmd[:50]
            return f"Command done (exit={exit_code}): {preview}"
        elif itype == "function_call":
            name = item.get("name", "")
            return f"Tool completed: {name}"
        elif itype == "function_call_output":
            output = item.get("output", "")
            preview = output[:80].replace("\n", " ") if output else ""
            return f"Tool output: {preview}..."
        return None

    elif etype == "response.output_text.delta":
        # Text streaming - too verbose, skip
        return None

    elif etype == "response.completed":
        return "Response completed"

    # Unknown event type - show raw
    return f"[{etype}]"


# --- Role prompt loading ---

def load_role_prompt(role: str) -> Optional[str]:
    """Load a role prompt file from codex-bridge/roles/."""
    role_file = ROLES_DIR / f"{role}.md"
    if role_file.exists():
        return role_file.read_text(encoding="utf-8")
    progress_warn(f"Role file not found: {role_file}")
    return None


# --- Session management ---

def load_sessions() -> dict:
    """Load sessions database."""
    if SESSIONS_FILE.exists():
        try:
            return json.loads(SESSIONS_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save_sessions(sessions: dict) -> None:
    """Save sessions database."""
    SESSIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    SESSIONS_FILE.write_text(json.dumps(sessions, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def record_session(thread_id: str, model: str, role: Optional[str], workdir: str) -> None:
    """Record a new session for later resume."""
    sessions = load_sessions()
    sessions[thread_id] = {
        "model": model,
        "role": role,
        "workdir": workdir,
        "created": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "last_active": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    save_sessions(sessions)
    progress_msg(f"Session saved: {thread_id[:12]}...")


# --- Build codex command ---

def build_codex_command(
    prompt: str,
    workdir: Optional[str],
    model: str,
    session_id: Optional[str],
    timeout: int,
) -> list[str]:
    """Build the wsl command to invoke codex exec."""
    cmd = ["wsl", "-d", WSL_DISTRO, "--", "bash", "-c"]

    # Build codex exec command
    parts = ["codex", "exec", "--json", "--skip-git-repo-check"]
    parts.append(f'-m "{model}"')

    if workdir:
        parts.append(f'-C "{workdir}"')

    if session_id:
        parts.append(f"resume {session_id}")

    # Prompt: pipe via stdin using heredoc to avoid shell escaping issues
    codex_cmd = " ".join(parts)
    # Use heredoc for prompt delivery (no timeout wrapper - Python handles timeout)
    inner = f'{codex_cmd} - <<\'GA_CODEX_EOF\'\n{prompt}\nGA_CODEX_EOF'
    cmd.append(inner)

    return cmd


# --- Main ---

def main() -> int:
    parser = argparse.ArgumentParser(
        description="GA→Codex bridge CLI with real-time progress",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("prompt", nargs="?", help="Task prompt for codex")
    parser.add_argument("--file", "-f", help="Read prompt from file")
    parser.add_argument("--progress", "-p", action="store_true", default=True,
                        help="Show real-time progress (default: True)")
    parser.add_argument("--session", "-s", help="Resume existing session ID")
    parser.add_argument("--workdir", "-w", help="Working directory (WSL path)")
    parser.add_argument("--role", "-r", help="Role prompt to load (architect/reviewer/analyzer/debugger/frontend)")
    parser.add_argument("--model", "-m", default=DEFAULT_MODEL, help=f"Model (default: {DEFAULT_MODEL})")
    parser.add_argument("--timeout", "-t", type=int, default=DEFAULT_TIMEOUT,
                        help=f"Timeout in seconds (default: {DEFAULT_TIMEOUT})")
    parser.add_argument("--no-progress", action="store_true", help="Disable progress output")
    parser.add_argument("--async", dest="async_mode", metavar="TASK_ID",
                        help="Async mode: write progress+result to temp/codex/TASK_ID.json")
    parser.add_argument("--save-session", action="store_true", default=True,
                        help="Save session ID for later resume (default: True)")

    args = parser.parse_args()

    # --- Resolve prompt ---
    if args.file:
        prompt_path = Path(args.file)
        if not prompt_path.exists():
            print(f"Error: prompt file not found: {args.file}", file=sys.stderr)
            return 1
        prompt = prompt_path.read_text(encoding="utf-8")
    elif args.prompt:
        prompt = args.prompt
    elif not sys.stdin.isatty():
        prompt = sys.stdin.read()
    else:
        parser.print_help()
        return 1

    # --- Prepend role prompt if specified ---
    if args.role:
        role_prompt = load_role_prompt(args.role)
        if role_prompt:
            prompt = f"{role_prompt}\n\n---\n\n{prompt}"

    show_progress = args.progress and not args.no_progress

    # --- Async mode: setup status file ---
    async_status_path = None
    if args.async_mode:
        async_dir = Path(__file__).parent / "temp" / "codex"
        async_dir.mkdir(parents=True, exist_ok=True)
        async_status_path = async_dir / f"{args.async_mode}.json"
        _write_async_status(async_status_path, status="running", progress="Starting codex...")

    # --- Build and execute ---
    if show_progress:
        progress_step(f"Starting codex (model={args.model})")
        if args.session:
            progress_msg(f"Resuming session: {args.session[:12]}...")
        if args.workdir:
            progress_msg(f"Workdir: {args.workdir}")
        if args.role:
            progress_msg(f"Role: {args.role}")

    cmd = build_codex_command(
        prompt=prompt,
        workdir=args.workdir,
        model=args.model,
        session_id=args.session,
        timeout=args.timeout,
    )

    if show_progress:
        progress_msg("Launching codex exec...")

    # Execute codex and stream JSONL
    thread_id = None
    final_output = []
    last_text = ""
    has_error = False

    timed_out = False

    def _kill_on_timeout(p):
        nonlocal timed_out
        timed_out = True
        try:
            p.kill()
        except OSError:
            pass

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )

        # Timer to force-kill codex subprocess after timeout
        timeout_sec = args.timeout if args.timeout and args.timeout > 0 else 0
        timer = threading.Timer(timeout_sec, _kill_on_timeout, args=[proc]) if timeout_sec > 0 else None
        if timer:
            timer.daemon = True
            timer.start()

        # Read stdout line by line (JSONL stream)
        for line in proc.stdout:
            event = parse_event(line)
            if event is None:
                # Non-JSON line, might be codex output
                final_output.append(line)
                continue

            etype = event.get("type", "")

            # Capture thread_id for session management
            if etype == "thread.started":
                thread_id = event.get("thread_id")
                if show_progress and thread_id:
                    progress_msg(f"Thread: {thread_id[:16]}...")
                if async_status_path and thread_id:
                    _write_async_status(async_status_path, "running",
                                       "Thread started", thread_id=thread_id)

            # Capture final message text
            if etype == "message.delta":
                delta = event.get("delta", "")
                if delta:
                    last_text += delta

            elif etype == "item.completed":
                item = event.get("item", {})
                itype = item.get("type", "")
                if itype == "agent_message":
                    last_text = item.get("text", last_text)
                    if async_status_path:
                        _write_async_status(async_status_path, "running",
                            f"Reply: {last_text[:80].replace(chr(10), ' ')}...",
                            thread_id=thread_id or "")
                elif itype == "command_execution":
                    cmd_desc = item.get("command", "")[:60]
                    if async_status_path:
                        _write_async_status(async_status_path, "running",
                            f"Command: {cmd_desc}", thread_id=thread_id or "")
                elif itype == "message":
                    content = item.get("content", [])
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "output_text":
                            last_text = block.get("text", last_text)

            elif etype == "response.completed":
                resp = event.get("response", {})
                output_items = resp.get("output", [])
                for oi in output_items:
                    if oi.get("type") == "message":
                        for c in oi.get("content", []):
                            if c.get("type") == "output_text":
                                last_text = c.get("text", last_text)

            # Show progress
            if show_progress:
                desc = describe_event(event)
                if desc:
                    if etype == "error" or etype == "turn.failed":
                        progress_error(desc)
                        has_error = True
                    elif "completed" in etype or "done" in etype:
                        progress_done(desc)
                    else:
                        progress_step(desc)

        proc.wait()

        # Cancel timer if still running
        if timer:
            timer.cancel()

        # Check if killed by timeout
        if timed_out:
            progress_error(f"Timeout after {timeout_sec}s")
            if async_status_path:
                _write_async_status(async_status_path, "error", f"Timeout after {timeout_sec}s")
            return 1

        # Read any stderr
        stderr_output = proc.stderr.read() if proc.stderr else ""
        if stderr_output and show_progress:
            for err_line in stderr_output.strip().split("\n"):
                if err_line.strip():
                    progress_warn(f"stderr: {err_line.strip()}")

    except FileNotFoundError:
        progress_error("wsl not found. This tool requires WSL.")
        if async_status_path:
            _write_async_status(async_status_path, "error", "wsl not found")
        return 1
    except Exception as e:
        progress_error(f"Unexpected error: {e}")
        if async_status_path:
            _write_async_status(async_status_path, "error", str(e))
        return 1

    # --- Save session ---
    if thread_id and args.save_session and not has_error:
        record_session(thread_id, args.model, args.role, args.workdir or "")

    # --- Output final result ---
    result = last_text.strip() if last_text.strip() else "".join(final_output).strip()

    # Async mode: write final result to status file
    if async_status_path:
        _write_async_status(async_status_path, "done", "Completed",
                           result=result[:8000], thread_id=thread_id or "")

    if result:
        # safe print: avoid GBK codec crash on Windows
        try:
            print(result)
        except UnicodeEncodeError:
            sys.stdout.buffer.write(result.encode("utf-8", errors="replace"))
            sys.stdout.buffer.write(b"\n")
    else:
        if show_progress:
            progress_warn("No text output from codex")
        return 1 if proc.returncode != 0 else 0

    return proc.returncode


if __name__ == "__main__":
    sys.exit(main())