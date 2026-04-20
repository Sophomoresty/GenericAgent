@echo off
REM ga-codex.bat - Windows entry point for ga-codex.py
REM Usage: ga-codex.bat "prompt" [--progress] [--session ID] ...
SETLOCAL
SET "SCRIPT_DIR=%~dp0"
"%SCRIPT_DIR%.venv\Scripts\python.exe" "%SCRIPT_DIR%ga-codex.py" %*
EXIT /B %ERRORLEVEL%
