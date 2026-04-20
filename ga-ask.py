"""ga-ask.py: One-shot GA query with progress, timeout, and structured output.

Usage:
    python ga-ask.py [--timeout SEC] [--json] "your question"

Queue events from agentmain.py:
    {'next': text, 'source': ...}  - intermediate progress
    {'done': full_text, 'source': ...}  - final result (includes errors)

Exit codes:
    0  success, result on stdout
    1  timeout
    2  GA internal error
    3  no query provided
"""
import sys, os, io, re, time, threading, argparse, json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from agentmain import GeneraticAgent

# --- Encoding helpers ---

def _clean_output(text):
    """Remove internal tags and debug noise from GA output."""
    # Remove <summary>...</summary> blocks
    text = re.sub(r'<summary>.*?</summary>\s*', '', text, flags=re.DOTALL)
    # Remove [Debug] lines
    text = re.sub(r'\[Debug\][^\n]*\n?', '', text)
    # Remove "LLM Running (Turn N) ..." in all formats (bold/plain, any trailing)
    text = re.sub(r'\*{0,2}LLM Running \(Turn \d+\)[^\n]*\n?', '', text)
    # Remove leading blank lines after cleanup
    return text.strip()

def _safe_print(text, file=None):
    """Print with GBK fallback for Windows console."""
    file = file or sys.stdout
    try:
        print(text, file=file)
    except UnicodeEncodeError:
        encoded = text.encode(getattr(file, 'encoding', 'utf-8') or 'utf-8', errors='replace')
        file.buffer.write(encoded)
        file.buffer.write(b'\n')
        file.flush()

def main():
    parser = argparse.ArgumentParser(description='One-shot GA query')
    parser.add_argument('query', nargs='*', help='Query text')
    parser.add_argument('--timeout', type=int, default=300, help='Timeout in seconds (default: 300)')
    parser.add_argument('--json', action='store_true', help='Output result as JSON')
    args = parser.parse_args()

    query = ' '.join(args.query).strip()
    if not query:
        try:
            query = input().strip()
        except EOFError:
            pass
    if not query:
        _safe_print(json.dumps({"status": "error", "error": "No query provided", "exit_code": 3}, ensure_ascii=False))
        return 3

    # --- Suppress debug prints from agent internals ---
    _real_stdout = sys.stdout
    sys.stdout = io.StringIO()

    agent = GeneraticAgent()
    agent.next_llm(0)
    agent.verbose = False
    threading.Thread(target=agent.run, daemon=True).start()

    dq = agent.put_task(query, source='task')
    result = None
    error_info = None
    last_progress_time = time.time()
    progress_count = 0

    while True:
        try:
            item = dq.get(timeout=min(30, args.timeout))
            if 'done' in item:
                result = item['done']
                break
            elif 'next' in item:
                # --- Progress feedback to stderr (non-blocking for codex) ---
                elapsed = time.time() - last_progress_time
                progress_count += 1
                if elapsed >= 10:  # Report progress every ~10 seconds
                    chunk = item.get('next', '')
                    preview = chunk[:100].replace('\n', ' ').strip()
                    _safe_print(f"[progress] turn chunk #{progress_count}: {preview}...", file=sys.stderr)
                    last_progress_time = time.time()
        except Exception:
            # Check total elapsed
            if time.time() - last_progress_time > args.timeout:
                sys.stdout = _real_stdout
                error_msg = f"Timeout after {args.timeout}s waiting for GA response"
                _safe_print(json.dumps({"status": "error", "error": error_msg, "exit_code": 1}, ensure_ascii=False))
                return 1

    # --- Restore stdout and output result ---
    sys.stdout = _real_stdout

    # Check for errors embedded in done text
    if result and 'Backend Error:' in result:
        error_info = result
    elif not result or not result.strip():
        error_info = "GA returned empty result"

    cleaned = _clean_output(result) if result else ''

    if args.json:
        out = {
            "status": "error" if error_info else "ok",
            "exit_code": 2 if error_info else 0,
        }
        if error_info:
            out["error"] = error_info
        else:
            out["result"] = cleaned
        _safe_print(json.dumps(out, ensure_ascii=False))
        return out["exit_code"]
    else:
        if error_info:
            _safe_print(json.dumps({"status": "error", "error": error_info, "exit_code": 2}, ensure_ascii=False))
            return 2
        if cleaned:
            _safe_print(cleaned)
        return 0

if __name__ == '__main__':
    sys.exit(main())