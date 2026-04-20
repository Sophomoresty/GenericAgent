@echo off
:: GA CLI wrapper - GenericAgent command line interface
:: Usage:
::   ga                     -> interactive mode
::   ga -t <task> -i "msg"  -> one-shot task mode (write input, wait for output)
::   ga -r <script>         -> reflect/monitor mode
::   ga --help              -> show help

setlocal
cd /d "D:\code\GenericAgent"
.venv\Scripts\python.exe agentmain.py %*
endlocal
