@echo off
REM ga-codex.bat - Windows entry point for ga-codex.py
REM Usage: ga-codex.bat [--progress] [--session ID] [--json] [--timeout SEC] "prompt"
chcp 65001 >nul 2>&1
SETLOCAL
SET "SCRIPT_DIR=%~dp0"
"%SCRIPT_DIR%.venv\Scripts\python.exe" -X utf8 "%SCRIPT_DIR%ga-codex.py" %*
EXIT /B %ERRORLEVEL%
