$ErrorActionPreference = "Continue"
$Host.UI.RawUI.WindowTitle = "AcademicReviewer - Backend"
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

Write-Host ""
Write-Host "  ================================================" -ForegroundColor Cyan
Write-Host "      AcademicReviewer - Backend (FastAPI)        " -ForegroundColor Cyan
Write-Host "  ================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Starting backend server..." -ForegroundColor Yellow
Write-Host "  API:  http://127.0.0.1:8000" -ForegroundColor White
Write-Host "  Docs: http://127.0.0.1:8000/docs" -ForegroundColor White
Write-Host ""

. $venvActivate
python run.py

Write-Host ""
Read-Host "Press Enter to exit"
