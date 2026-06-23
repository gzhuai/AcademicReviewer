@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0.."

:: Check if PowerShell is available
where powershell >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [X] PowerShell not found on this system.
    echo.
    echo     Please install PowerShell from https://github.com/PowerShell/PowerShell
    echo     Or set up manually:
    echo       1. python -m venv venv
    echo       2. venv\Scripts\pip install -r requirements.txt
    echo       3. copy .env.example .env  (then edit with your API keys)
    echo.
    pause
    exit /b 1
)

powershell -ExecutionPolicy Bypass -File "%~dp0install.ps1"
pause
