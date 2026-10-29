param(
    [string]$Model = "qwen2.5:7b",
    [string]$AppRepoUrl = "",
    [string]$InstallVSCode = "true"
)

# Bootstrap for the AI security lab Windows demo box.
# Runs under the Custom Script Extension (SYSTEM context) at first boot.
# Installs Chrome, Firefox, Python, Git (+ optional VS Code) machine-wide via
# Chocolatey, installs Ollama with a shared model directory, pulls the model,
# and (optionally) deploys the demo app. Logs to C:\bootstrap.log.

$ErrorActionPreference = "Continue"
$ProgressPreference = "SilentlyContinue"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

function Log($m) { Write-Output ("[{0}] {1}" -f (Get-Date -Format "HH:mm:ss"), $m) }

Log "bootstrap start. model=$Model vscode=$InstallVSCode apprepo=$AppRepoUrl"

# --- Chocolatey --------------------------------------------------------------
if (-not (Get-Command choco -ErrorAction SilentlyContinue)) {
    Log "installing Chocolatey"
    Set-ExecutionPolicy Bypass -Scope Process -Force
    Invoke-Expression ((New-Object Net.WebClient).DownloadString("https://community.chocolatey.org/install.ps1"))
}
$env:Path += ";C:\ProgramData\chocolatey\bin"

# --- Packages (machine-wide, available to all users) -------------------------
$pkgs = @("git", "python", "googlechrome", "firefox", "7zip")
if ($InstallVSCode -eq "true") { $pkgs += "vscode" }
foreach ($p in $pkgs) {
    Log "choco install $p"
    choco install $p -y --no-progress --ignore-checksums
}

# refresh PATH for this session
try {
    Import-Module "$env:ChocolateyInstall\helpers\chocolateyProfile.psm1" -ErrorAction SilentlyContinue
    refreshenv
} catch { }
$env:Path += ";C:\Program Files\Git\cmd;C:\Python312;C:\Python312\Scripts"

# --- Ollama with a SHARED model directory ------------------------------------
# A machine-wide OLLAMA_MODELS dir means the model this (SYSTEM) run pulls is the
# same one the interactive RDP user sees.
$ollamaModels = "C:\ollama-models"
New-Item -ItemType Directory -Force -Path $ollamaModels | Out-Null
[Environment]::SetEnvironmentVariable("OLLAMA_MODELS", $ollamaModels, "Machine")
$env:OLLAMA_MODELS = $ollamaModels

Log "installing Ollama"
$ollamaOk = $false
try {
    choco install ollama -y --no-progress --ignore-checksums
    if (Get-Command ollama -ErrorAction SilentlyContinue) { $ollamaOk = $true }
} catch { Log "choco ollama failed: $_" }

if (-not $ollamaOk) {
    Log "falling back to official Ollama installer"
    try {
        $oll = "$env:TEMP\OllamaSetup.exe"
        Invoke-WebRequest -Uri "https://ollama.com/download/OllamaSetup.exe" -OutFile $oll
        Start-Process -FilePath $oll -ArgumentList "/VERYSILENT", "/NORESTART" -Wait
    } catch { Log "official Ollama install failed: $_" }
}

# make sure ollama is on PATH for this session (common install locations)
foreach ($d in @("C:\ProgramData\chocolatey\bin",
                 "C:\Program Files\Ollama",
                 "$env:LOCALAPPDATA\Programs\Ollama")) {
    if (Test-Path $d) { $env:Path += ";$d" }
}

# --- Pull the model ----------------------------------------------------------
if (Get-Command ollama -ErrorAction SilentlyContinue) {
    Log "starting ollama serve"
    Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden
    Start-Sleep -Seconds 10
    Log "pulling model $Model (this can take several minutes)"
    & ollama pull $Model
    Log "model pull finished"
} else {
    Log "WARNING: ollama not found on PATH; pull the model after first login: ollama pull $Model"
}

# --- Optional: deploy the demo app ------------------------------------------
if ($AppRepoUrl -ne "") {
    Log "cloning demo app from $AppRepoUrl"
    $dest = "C:\straiker-demo"
    try {
        & git clone $AppRepoUrl $dest
        $appdir = $dest
        if (Test-Path (Join-Path $dest "app")) { $appdir = Join-Path $dest "app" }

        if (Test-Path (Join-Path $appdir "requirements.txt")) {
            Log "setting up Python venv in $appdir"
            Push-Location $appdir
            & python -m venv .venv
            & ".\.venv\Scripts\python.exe" -m pip install --upgrade pip
            & ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt

            if ((Test-Path ".env.example") -and (-not (Test-Path ".env"))) {
                Copy-Item ".env.example" ".env"
                (Get-Content ".env") -replace "OLLAMA_MODEL=.*", "OLLAMA_MODEL=$Model" | Set-Content ".env"
            }
            Pop-Location

            # Desktop shortcut for all users
            if (Test-Path (Join-Path $appdir "start-demo.ps1")) {
                $lnk = "C:\Users\Public\Desktop\Start Straiker Demo.lnk"
                $ws = New-Object -ComObject WScript.Shell
                $sc = $ws.CreateShortcut($lnk)
                $sc.TargetPath = "powershell.exe"
                $sc.Arguments = "-ExecutionPolicy Bypass -NoExit -File `"$appdir\start-demo.ps1`""
                $sc.WorkingDirectory = $appdir
                $sc.IconLocation = "powershell.exe,0"
                $sc.Save()
                Log "created desktop shortcut"
            }
        } else {
            Log "no requirements.txt found under $appdir; skipping venv setup"
        }
    } catch { Log "app deploy failed: $_" }
} else {
    Log "app_repo_url empty; prerequisites only"
}

Log "bootstrap complete"
