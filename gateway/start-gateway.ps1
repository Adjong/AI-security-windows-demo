# start-gateway.ps1 - launch the LiteLLM gateway + web monitor (Windows)
#
# LiteLLM gets its OWN venv (.venv-gateway) on purpose: it pulls dependencies
# (incl. a newer 'mcp') that would otherwise break the MCP servers' global env,
# which needs mcp<2. Isolating it here keeps both happy.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path ".venv-gateway")) {
    Write-Host "Creating gateway venv (.venv-gateway) and installing LiteLLM..." -ForegroundColor Yellow
    python -m venv .venv-gateway
}
& ".\.venv-gateway\Scripts\Activate.ps1"
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements-gateway.txt

Start-Job { Start-Sleep 6; Start-Process "http://127.0.0.1:8820" } | Out-Null
Write-Host "Gateway monitor on http://127.0.0.1:8820  (LiteLLM on :4000)  Ctrl+C to stop" -ForegroundColor Green
python -m uvicorn monitor:app --host 127.0.0.1 --port 8820
