@echo off
title AI Startup Launch Assistant
echo ======================================================================
echo   Starting AI Startup Launch Assistant...
echo ======================================================================
echo.

cd /d "%~dp0"

where py >nul 2>&1
if %ERRORLEVEL% equ 0 (
    set PYTHON_CMD=py
    goto found_python
)

where python >nul 2>&1
if %ERRORLEVEL% equ 0 (
    set PYTHON_CMD=python
    goto found_python
)

echo [ERROR] Python was not found in your PATH.
pause
exit /b 1

:found_python
%PYTHON_CMD% -m pip install -q -r requirements.txt
start "" "http://127.0.0.1:5000"
%PYTHON_CMD% app.py
pause
