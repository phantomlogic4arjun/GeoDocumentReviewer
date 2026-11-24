$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " GeoDocumentReviewer - Windows Setup"
Write-Host "========================================" -ForegroundColor Cyan

# Check Windows Package Manager
if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
    throw "winget is unavailable. Install Microsoft App Installer first."
}

# Check Python 3.12
$pythonAvailable = $false
py -3.12 --version

if ($LASTEXITCODE -eq 0) {
    $pythonAvailable = $true
}

if (-not $pythonAvailable) {
    Write-Host "Installing Python 3.12..." -ForegroundColor Yellow

    winget install --id Python.Python.3.12 --exact `
        --accept-package-agreements --accept-source-agreements

    if ($LASTEXITCODE -ne 0) {
        throw "Python installation failed."
    }

    Write-Host "Restart PowerShell and run setup_windows.ps1 again."
    exit 0
}

# Create virtual environment
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "Creating virtual environment..."
    py -3.12 -m venv .venv
}

$venvPython = ".\.venv\Scripts\python.exe"

# Install application and development dependencies
Write-Host "Installing Python dependencies..."

& $venvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) {
    throw "pip upgrade failed."
}

& $venvPython -m pip install -e ".[dev]"
if ($LASTEXITCODE -ne 0) {
    throw "Project dependency installation failed."
}

# Create .env if it does not exist
if (-not (Test-Path ".env")) {
    if (-not (Test-Path ".env.example")) {
        throw ".env.example is missing."
    }

    Copy-Item ".env.example" ".env"
    Write-Host "Created .env from .env.example."
}

# Check Tesseract OCR
$tesseractPath = "C:\Program Files\Tesseract-OCR\tesseract.exe"

if (-not (Get-Command tesseract -ErrorAction SilentlyContinue) -and
    -not (Test-Path $tesseractPath)) {

    Write-Host "Installing Tesseract OCR..." -ForegroundColor Yellow

    winget install --id UB-Mannheim.TesseractOCR --exact `
        --accept-package-agreements --accept-source-agreements

    if ($LASTEXITCODE -ne 0) {
        throw "Tesseract installation failed. Install it manually from https://github.com/UB-Mannheim/tesseract/wiki"
    }
}

# Configure Tesseract in .env when installed at the standard location
if (Test-Path $tesseractPath) {
    $content = Get-Content ".env" -Raw

    if ($content -match "(?m)^TESSERACT_CMD=") {
        $content = [regex]::Replace(
            $content,
            "(?m)^TESSERACT_CMD=.*$",
            "TESSERACT_CMD=$tesseractPath"
        )
    }
    else {
        $content += "`r`nTESSERACT_CMD=$tesseractPath`r`n"
    }

    $utf8 = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText(
        (Join-Path (Get-Location) ".env"),
        $content,
        $utf8
    )
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host " Setup completed!"
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:"
Write-Host "1. Add your OpenRouter API key to .env."
Write-Host "2. Run .\run_windows.ps1"
Write-Host ""
