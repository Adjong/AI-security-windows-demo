# start-demo.ps1 - one-command launcher for the Straiker lab demo dashboard (Windows)
# Usage:  right-click > Run with PowerShell, or:  powershell -ExecutionPolicy Bypass -File .\start-demo.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== Straiker lab demo dashboard ===" -ForegroundColor Cyan

# 1. Python check
try { $pyv = (python --version) 2>&1 } catch { Write-Host "Python not found on PATH. Install Python 3.11+ and retry." -ForegroundColor Red; exit 1 }
Write-Host "Python: $pyv"

# 2. Virtual environment + dependencies
if (-not (Test-Path ".venv")) {
    Write-Host "Creating virtual environment (.venv)..."
    python -m venv .venv
}
& ".\.venv\Scripts\Activate.ps1"
Write-Host "Installing dependencies..."
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt

# 3. .env check
if (-not (Test-Path ".env")) {
    Write-Host "No .env found - copying .env.example to .env. Edit it to add your Straiker key." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
}

# 4. Ollama / model check (warn only)
try {
    $models = (ollama list) 2>&1
    if ($models -notmatch "qwen2.5") {
        Write-Host "qwen2.5 not found in Ollama. Run: ollama pull qwen2.5:7b" -ForegroundColor Yellow
    } else { Write-Host "Ollama model present." }
} catch { Write-Host "Ollama not detected on PATH. Install from https://ollama.com and run: ollama pull qwen2.5:7b" -ForegroundColor Yellow }

# 5. Open the browser shortly after the server starts
Start-Job { Start-Sleep 4; Start-Process "http://127.0.0.1:8800" } | Out-Null

# 6. Launch the app (serves UI + starts sink + CRM + notes servers)
Write-Host "Starting dashboard on http://127.0.0.1:8800  (Ctrl+C to stop)" -ForegroundColor Green
python -m uvicorn app:app --host 127.0.0.1 --port 8800
