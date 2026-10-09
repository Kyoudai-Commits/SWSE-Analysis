@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Creating a private Python environment...
    py -3 -m venv .venv
    if errorlevel 1 goto python_error
)

".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt
if errorlevel 1 goto dependency_error

".venv\Scripts\python.exe" -c "import tkinter" >nul 2>&1
if errorlevel 1 goto tkinter_error

if exist ".venv\Scripts\pythonw.exe" (
    start "" ".venv\Scripts\pythonw.exe" "scripts\swse_scraper_gui.py"
) else (
    start "" ".venv\Scripts\python.exe" "scripts\swse_scraper_gui.py"
)
exit /b 0

:python_error
echo.
echo Python 3 could not be found. Install Python 3.10 or newer, then try again.
echo During setup, enable the option to install Tcl/Tk if offered.
pause
exit /b 1

:dependency_error
echo.
echo Could not install the downloader's Python packages. Check your internet connection and try again.
pause
exit /b 1

:tkinter_error
echo.
echo Tkinter/Tcl-Tk is missing. Repair or reinstall Python with Tcl/Tk support enabled, then try again.
pause
exit /b 1
