# install functions

Function Install-Winget {
    Install-Script -Name winget-install -Force
    winget-install -Force
    }

Function Install-supporting-apps {
    #Pyhton
    winget install -e --id Python.Python.3.12
    #Ollama
    winget install -e --id Ollama.Ollama
    #GIT & GH
    winget install --id Git.Git -e --source winget
    winget install --id GitHub.CLI
    #VS Code
    winget install --id Microsoft.VisualStudioCode -e
    #7-ZIP
    winget install --id 7zip.7zip -e
    }


function Update-SessionPath {
    $m = [Environment]::GetEnvironmentVariable('Path','Machine')
    $u = [Environment]::GetEnvironmentVariable('Path','User')
    $env:Path = "$m;$u"
}

Function Install-Python-Packages {
    #set PATH to Python
    #[Environment]::SetEnvironmentVariable("Path", ([Environment]::GetEnvironmentVariable("Path", "User") + ";C:\Users\azureuser\AppData\Local\Programs\Python;C:\Users\azureuser\AppData\Local\Programs\Python\Scripts"), "User")
    python -m pip install --upgrade pip
    python -m pip install "fastapi>=0.110,<1"
    python -m pip install "uvicorn[standard]>=0.29,<1" 
    python -m pip install "mcp>=1.2,<2"
    python -m pip install "ollama>=0.3,<1" 
    python -m pip install "openai>=1.30,<2"
    }

Function Install-Ollama-model {
    ollama pull qwen2.5:7b
}

Function Install-Browsers {
    winget install --id Google.Chrome -e
    winget install --id Mozilla.Firefox -e
    }

# Install winget
Install-Winget
# Install prerequisites
Install-supporting-apps
# Set path to Python & Ollama
update-Sessionpath
# Install Pyhton packages
Install-Python-Packages
# Install Ollama model
Install-Ollama-model
# Install browsers
Install-Browsers
