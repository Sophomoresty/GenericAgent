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
set "GA_GUI_ARGS=ga-gui.pyw"
if not "%~1"=="" set "GA_GUI_ARGS=%GA_GUI_ARGS% %~1"
if not "%~2"=="" set "GA_GUI_ARGS=%GA_GUI_ARGS% %~2"
if not "%~3"=="" set "GA_GUI_ARGS=%GA_GUI_ARGS% %~3"
if not "%~4"=="" set "GA_GUI_ARGS=%GA_GUI_ARGS% %~4"
if not "%~5"=="" set "GA_GUI_ARGS=%GA_GUI_ARGS% %~5"
if not "%~6"=="" set "GA_GUI_ARGS=%GA_GUI_ARGS% %~6"
if not "%~7"=="" set "GA_GUI_ARGS=%GA_GUI_ARGS% %~7"
if not "%~8"=="" set "GA_GUI_ARGS=%GA_GUI_ARGS% %~8"
if not "%~9"=="" set "GA_GUI_ARGS=%GA_GUI_ARGS% %~9"
powershell -NoProfile -WindowStyle Hidden -Command "Start-Process -WindowStyle Hidden -FilePath '.venv\Scripts\pythonw.exe' -ArgumentList '%GA_GUI_ARGS%' -WorkingDirectory 'D:\code\GenericAgent'"
endlocal
