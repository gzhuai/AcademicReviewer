$ErrorActionPreference = "Continue"
$Host.UI.RawUI.WindowTitle = "AcademicReviewer - Frontend"
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
Write-Host "      AcademicReviewer - Frontend (Gradio)        " -ForegroundColor Cyan
Write-Host "  ================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Starting Gradio UI..." -ForegroundColor Yellow
Write-Host "  URL: http://127.0.0.1:7860" -ForegroundColor White
Write-Host ""

. $venvActivate
python app/gradio_app.py

Write-Host ""
Read-Host "Press Enter to exit"
