@echo off
:: ga-ask: One-shot GA call. Args: [--timeout SEC] [--json] <prompt>
:: Usage: ga-ask "your question here"
:: Usage: ga-ask --timeout 600 --json "complex task"
chcp 65001 >nul 2>&1
cd /d "D:\code\GenericAgent"
.venv\Scripts\python.exe -X utf8 ga-ask.py %*