$ErrorActionPreference = "Stop"

$venvPython = ".\.venv\Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    Write-Host "Virtual environment missing. Run .\setup_windows.ps1 first." -ForegroundColor Red
    exit 1
}

if (-not (Test-Path ".env")) {
    Write-Host ".env missing. Run .\setup_windows.ps1 first." -ForegroundColor Red
    exit 1
}

Write-Host "Starting GeoDocumentReviewer..." -ForegroundColor Cyan

& $venvPython -m streamlit run app.py

if ($LASTEXITCODE -ne 0) {
    Write-Host "Streamlit exited with an error." -ForegroundColor Red
    exit $LASTEXITCODE
}
