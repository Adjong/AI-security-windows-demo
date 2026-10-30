# start-all.ps1 - launch the whole AI security demo in the right order.
# Place at the repo root (the folder that contains mcp\, agent\, gateway\).
# Each component opens in its own titled PowerShell window; this launcher waits
# for dependencies between steps so nothing starts before what it needs.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Test-Port($p) {
    try { $c = New-Object Net.Sockets.TcpClient; $c.Connect("127.0.0.1", $p); $c.Close(); return $true }
    catch { return $false }
}
function Wait-Port($p, $t = 60) {
    $end = (Get-Date).AddSeconds($t)
    while ((Get-Date) -lt $end) { if (Test-Port $p) { return $true }; Start-Sleep 1 }
    return $false
}
function Start-Component($title, $script) {
    if (-not (Test-Path $script)) { Write-Host "MISSING: $script" -ForegroundColor Red; return }
    $cmd = "`$host.ui.RawUI.WindowTitle='$title'; & '$script'"
    Start-Process powershell -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-Command", $cmd
}

Write-Host "=== Starting AI Security Demo ===" -ForegroundColor Cyan

# 1. Ollama (model backend) - start if not already serving
if (Test-Port 11434) {
    Write-Host "Ollama: already running"
} else {
    Write-Host "Ollama: starting..."
    Start-Process ollama -ArgumentList "serve" -WindowStyle Hidden
    if (Wait-Port 11434 30) { Write-Host "Ollama: up" } else { Write-Host "Ollama: WARNING not responding on 11434" -ForegroundColor Yellow }
}

# 2. MCP control panel (sink + crm + notes) - must be up before the agent
Write-Host "MCP panel: launching..."
Start-Component "MCP Panel (8800)" "$PSScriptRoot\mcp\start-panel.ps1"
if (Wait-Port 9910 60) { Write-Host "MCP servers: up (crm 9910)" } else { Write-Host "MCP servers: WARNING crm 9910 not up" -ForegroundColor Yellow }
Wait-Port 9930 20 | Out-Null
Wait-Port 9900 20 | Out-Null

# 3. Gateway (LiteLLM 4000 + monitor 8820)
Write-Host "Gateway: launching..."
Start-Component "Gateway (monitor 8820 / LiteLLM 4000)" "$PSScriptRoot\gateway\start-gateway.ps1"

# 4. Agent (8810) - needs the MCP servers + Ollama, both up by now
Write-Host "Agent: launching..."
Start-Component "Agent (8810)" "$PSScriptRoot\agent\start-agent.ps1"

Write-Host ""
Write-Host "Launched. Each component is in its own window." -ForegroundColor Green
Write-Host "  Control panel  : http://127.0.0.1:8800"
Write-Host "  Agent          : http://127.0.0.1:8810"
Write-Host "  Gateway monitor: http://127.0.0.1:8820  (LiteLLM proxy on :4000)"
Write-Host ""
Write-Host "Each window opens its own browser tab. The gateway takes ~15-30s on first"
Write-Host "start while LiteLLM boots. Close a component's window (Ctrl+C) to stop it."
Read-Host "Press Enter to close THIS launcher (the component windows keep running)"
