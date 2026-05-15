$ErrorActionPreference = "Continue"
$Host.UI.RawUI.WindowTitle = "AcademicReviewer Launcher"
[Console]::OutputEncoding = [Text.Encoding]::UTF8

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$venvActivate = "venv\Scripts\Activate.ps1"

if (-not (Test-Path $venvActivate)) {
    Write-Host "[X] Virtual environment not found. Please run install first:" -ForegroundColor Red
    Write-Host "    scripts\install.bat" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "Starting backend (wait 5s for initialization)..." -ForegroundColor Green
$backendPs1 = Join-Path $PSScriptRoot "start_backend.ps1"
$frontendPs1 = Join-Path $PSScriptRoot "start_frontend.ps1"

Start-Process powershell -ArgumentList "-NoExit -ExecutionPolicy Bypass -File", "`"$backendPs1`""
Start-Sleep 5

Write-Host "Starting frontend..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit -ExecutionPolicy Bypass -File", "`"$frontendPs1`""
Start-Sleep 8

Write-Host "Opening browser..." -ForegroundColor Green
Start-Process "http://127.0.0.1:7860"
Write-Host "Frontend: http://127.0.0.1:7860" -ForegroundColor Cyan
Write-Host "Backend:  http://127.0.0.1:8000/docs" -ForegroundColor Cyan
