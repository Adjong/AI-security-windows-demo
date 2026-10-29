# start-agent.ps1 - launch the agent web interface (Windows)
# Assumes prerequisites (Python + packages) are installed and the MCP control
# panel (sink + crm + notes) and Ollama are already running.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Start-Job { Start-Sleep 4; Start-Process "http://127.0.0.1:8810" } | Out-Null
Write-Host "Agent on http://127.0.0.1:8810  (Ctrl+C to stop)" -ForegroundColor Green
python -m uvicorn agent:app --host 127.0.0.1 --port 8810
