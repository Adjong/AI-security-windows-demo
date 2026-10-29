# start-panel.ps1 - launch the MCP control panel (Windows)
# Usage: powershell -ExecutionPolicy Bypass -File .\start-panel.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path ".venv")) { python -m venv .venv }
& ".\.venv\Scripts\Activate.ps1"
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt

Start-Job { Start-Sleep 4; Start-Process "http://127.0.0.1:8800" } | Out-Null
Write-Host "MCP control panel on http://127.0.0.1:8800  (Ctrl+C to stop)" -ForegroundColor Green
python -m uvicorn panel:app --host 127.0.0.1 --port 8800
