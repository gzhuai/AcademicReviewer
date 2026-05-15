$ErrorActionPreference = "Continue"
$Host.UI.RawUI.WindowTitle = "AcademicReviewer Installer"
[Console]::OutputEncoding = [Text.Encoding]::UTF8

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

Write-Host ""
Write-Host "  ================================================" -ForegroundColor Cyan
Write-Host "      AcademicReviewer - One-Click Installer      " -ForegroundColor Cyan
Write-Host "  ================================================" -ForegroundColor Cyan
Write-Host ""

$REQUIRED_PYTHON = "3.10"

Write-Host "[Step 1/5] Detecting Python ${REQUIRED_PYTHON}+ ..." -ForegroundColor Yellow

function Test-PythonVersion($exe) {
    try {
        $out = & $exe --version 2>&1
        if ($LASTEXITCODE -eq 0) {
            if ($out -match "Python\s+(\d+)\.(\d+)") {
                $major = [int]$Matches[1]
                $minor = [int]$Matches[2]
                if ($major -gt 3 -or ($major -eq 3 -and $minor -ge 10)) {
                    return $true
                }
                Write-Host "    Found Python $major.$minor (need ${REQUIRED_PYTHON}+)" -ForegroundColor DarkYellow
                return $false
            }
            Write-Host "    Could not parse version from: $out" -ForegroundColor DarkYellow
            return $false
        }
    } catch {
        return $false
    }
    return $false
}

$pythonCmd = $null
foreach ($cmd in @("python", "python3", "py")) {
    Write-Host "    Trying '$cmd'..." -ForegroundColor Gray
    if (Test-PythonVersion $cmd) {
        $pythonCmd = $cmd
        $ver = & $cmd --version 2>&1
        Write-Host "    [OK] $ver" -ForegroundColor Green
        break
    }
}

if (-not $pythonCmd) {
    Write-Host ""
    Write-Host "[X] Python ${REQUIRED_PYTHON}+ not found!" -ForegroundColor Red
    Write-Host "    Please install Python ${REQUIRED_PYTHON}+ from https://www.python.org/downloads/" -ForegroundColor Red
    Write-Host "    IMPORTANT: Check 'Add Python to PATH' during installation." -ForegroundColor Red
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host ""

Write-Host "[Step 2/5] Creating virtual environment ..." -ForegroundColor Yellow
if (Test-Path "venv") {
    Write-Host "    venv already exists, skipping." -ForegroundColor DarkYellow
} else {
    $createResult = & $pythonCmd -m venv venv 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[X] Failed to create venv:" -ForegroundColor Red
        Write-Host "    $createResult" -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
    Write-Host "    [OK] venv created" -ForegroundColor Green
}

Write-Host ""

Write-Host "[Step 3/5] Installing dependencies ..." -ForegroundColor Yellow
Write-Host "    This may take a few minutes on first run..." -ForegroundColor Gray

$activateScript = "venv\Scripts\Activate.ps1"
$pipExe = "venv\Scripts\pip.exe"

if (Test-Path $activateScript) {
    & $pipExe install -r requirements.txt --quiet
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[!] pip install failed (check network). Retrying without --quiet..." -ForegroundColor DarkYellow
        & $pipExe install -r requirements.txt
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[X] pip install failed. Please check your network connection." -ForegroundColor Red
            Write-Host "    You can retry manually:" -ForegroundColor Red
            Write-Host "      cd scripts && powershell -ExecutionPolicy Bypass -File install.ps1" -ForegroundColor Gray
            Read-Host "Press Enter to exit"
            exit 1
        }
    }
    Write-Host "    [OK] Dependencies installed" -ForegroundColor Green
} else {
    Write-Host "[X] Activation script not found: $activateScript" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host ""

Write-Host "[Step 4/5] Setting up .env configuration ..." -ForegroundColor Yellow
if (-not (Test-Path ".env")) {
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" ".env"
        Write-Host "    [OK] Created .env from .env.example" -ForegroundColor Green
    } else {
        @"
# AcademicReviewer Configuration
# At least one API key is required
DEEPSEEK_API_KEY=
OPENAI_API_KEY=
GEMINI_API_KEY=
GLM_API_KEY=
LLM_PROVIDER=deepseek
"@ | Out-File -FilePath ".env" -Encoding UTF8
        Write-Host "    [OK] Created .env (please fill in your API keys)" -ForegroundColor Green
    }

    Write-Host ""
    $editChoice = Read-Host "    Edit .env now? (y/n) [y]"
    if ($editChoice -eq "" -or $editChoice -eq "y" -or $editChoice -eq "Y") {
        notepad ".env"
    }
} else {
    Write-Host "    .env already exists, skipping." -ForegroundColor DarkYellow
}

Write-Host ""

Write-Host "[Step 5/5] Creating data directories ..." -ForegroundColor Yellow
foreach ($dir in @("data\submissions", "data\chroma", "data\calibration")) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Write-Host "    Created: $dir" -ForegroundColor Gray
    }
}
Write-Host "    [OK] Data directories ready" -ForegroundColor Green

Write-Host ""
Write-Host "  ================================================" -ForegroundColor Cyan
Write-Host "      Installation Complete!" -ForegroundColor Green
Write-Host "  ================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Next steps:" -ForegroundColor White
Write-Host "    1. Make sure .env has your API keys" -ForegroundColor White
Write-Host "    2. Run:  scripts\start_all.bat  (launch backend + frontend)" -ForegroundColor White
Write-Host "    3. Open: http://127.0.0.1:7860  in browser" -ForegroundColor White
Write-Host ""

Read-Host "Press Enter to exit"
