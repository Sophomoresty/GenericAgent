@echo off
:: ga-ask: One-shot GA call. Args: <prompt>
:: Usage: ga-ask "your question here"
cd /d "D:\code\GenericAgent"
.venv\Scripts\python.exe ga-ask.py %*
endlocal