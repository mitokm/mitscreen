@echo off
rem Launch Mitscreen without a console window.
setlocal
cd /d "%~dp0"
if exist "%~dp0.venv\Scripts\pythonw.exe" (
    start "" "%~dp0.venv\Scripts\pythonw.exe" "%~dp0run.pyw"
) else (
    start "" pythonw "%~dp0run.pyw"
)
endlocal
