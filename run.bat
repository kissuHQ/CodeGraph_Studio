@echo off
setlocal
title CodeGraph Studio
cd /d "%~dp0"

if "%~1" NEQ "" (
    python "%~dp0codegraph.py" "%~1"
) else (
    python "%~dp0codegraph.py"
)

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [!] An error occurred. Make sure Python 3 is installed and available in PATH.
    pause
)
