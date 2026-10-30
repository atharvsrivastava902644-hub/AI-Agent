@echo off
title AI Startup Launch Assistant & All-in-One AI Platform
color 0B
echo ======================================================================
echo    Starting AI Startup Launch Assistant & All-in-One AI Platform
echo ======================================================================
echo.

where py >nul 2>nul
if %errorlevel% equ 0 (
    set PYTHON_CMD=py
    goto :FOUND_PYTHON
)

where python >nul 2>nul
if %errorlevel% equ 0 (
    set PYTHON_CMD=python
    goto :FOUND_PYTHON
)

echo [ERROR] Python was not found on your system!
echo Please install Python 3.10+ from https://www.python.org/
pause
exit /b 1

:FOUND_PYTHON
echo [1/3] Detected Python: %PYTHON_CMD%
echo [2/3] Checking dependencies...
%PYTHON_CMD% -m pip install -q -r requirements.txt

echo [3/3] Opening browser and starting server on http://127.0.0.1:5000 ...
start "" http://127.0.0.1:5000

%PYTHON_CMD% app.py

pause
