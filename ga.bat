@echo off
:: GA CLI wrapper - GenericAgent command line interface
:: Usage:
::   ga                     -> interactive mode
::   ga gui [--tg] [--qq]   -> launch GUI (Streamlit + pywebview, no terminal)
::   ga -t <task> -i "msg"  -> one-shot task mode (write input, wait for output)
::   ga -r <script>         -> reflect/monitor mode
::   ga --help              -> show help

setlocal
cd /d "D:\code\GenericAgent"

if /I "%~1"=="gui" goto gui

.venv\Scripts\python.exe agentmain.py %*
endlocal
goto :eof

:gui
shift
.venv\Scripts\pythonw.exe ga-gui.pyw %1 %2 %3 %4 %5 %6 %7 %8 %9
endlocal
