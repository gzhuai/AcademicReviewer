@echo off
cd /d "%~dp0.."
powershell -ExecutionPolicy Bypass -File "%~dp0start_frontend.ps1"
pause
