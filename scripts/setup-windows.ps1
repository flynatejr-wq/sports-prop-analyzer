#Requires -RunAsAdministrator
<#
.SYNOPSIS
    PropEdge AI — Complete Windows development environment setup
.DESCRIPTION
    Installs all prerequisites and configures the PropEdge AI platform for
    local development on Windows 10/11. Run this script ONCE from an elevated
    (Administrator) PowerShell terminal.
.EXAMPLE
    Set-ExecutionPolicy Bypass -Scope Process -Force
    .\scripts\setup-windows.ps1
#>

$ErrorActionPreference = "Stop"
$ProgressPreference    = "SilentlyContinue"   # speeds up Invoke-WebRequest

# ── Helpers ──────────────────────────────────────────────────────────────────
function Write-Step  { param($msg) Write-Host "`n[STEP] $msg" -ForegroundColor Cyan }
function Write-OK    { param($msg) Write-Host "  [OK]  $msg" -ForegroundColor Green }
function Write-Warn  { param($msg) Write-Host " [WARN] $msg" -ForegroundColor Yellow }
function Write-Fail  { param($msg) Write-Host " [FAIL] $msg" -ForegroundColor Red; exit 1 }

function Test-Command {
    param($Name)
    $null -ne (Get-Command $Name -ErrorAction SilentlyContinue)
}

function Install-Winget-Package {
    param($Id, $Name)
    Write-Host "  Installing $Name..." -ForegroundColor Gray
    winget install --id $Id --silent --accept-package-agreements --accept-source-agreements
}

# ── 0. Check Windows version ─────────────────────────────────────────────────
Write-Step "Checking Windows version"
$ver = [System.Environment]::OSVersion.Version
if ($ver.Major -lt 10) { Write-Fail "Windows 10 or 11 required (detected $ver)" }
Write-OK "Windows $($ver.Major).$($ver.Minor) — OK"

# ── 1. Install winget (if missing) ───────────────────────────────────────────
Write-Step "Checking winget (Windows Package Manager)"
if (-not (Test-Command "winget")) {
    Write-Warn "winget not found — installing via Add-AppxPackage"
    $url = "https://github.com/microsoft/winget-cli/releases/latest/download/Microsoft.DesktopAppInstaller_8wekyb3d8bbwe.msixbundle"
    $out = "$env:TEMP\winget.msixbundle"
    Invoke-WebRequest $url -OutFile $out
    Add-AppxPackage $out
} else {
    Write-OK "winget found: $(winget --version)"
}

# ── 2. Git ────────────────────────────────────────────────────────────────────
Write-Step "Git"
if (-not (Test-Command "git")) {
    Install-Winget-Package "Git.Git" "Git"
    $env:PATH += ";C:\Program Files\Git\cmd"
} else { Write-OK "git $(git --version)" }

# ── 3. Node.js LTS ───────────────────────────────────────────────────────────
Write-Step "Node.js (LTS)"
if (-not (Test-Command "node")) {
    Install-Winget-Package "OpenJS.NodeJS.LTS" "Node.js LTS"
    $env:PATH += ";C:\Program Files\nodejs"
} else { Write-OK "node $(node --version)" }

# ── 4. Python 3.11 ───────────────────────────────────────────────────────────
Write-Step "Python 3.11"
if (-not (Test-Command "python")) {
    Install-Winget-Package "Python.Python.3.11" "Python 3.11"
    $env:PATH += ";$env:LOCALAPPDATA\Programs\Python\Python311;$env:LOCALAPPDATA\Programs\Python\Python311\Scripts"
} else {
    $pyver = python --version
    Write-OK $pyver
}

# ── 5. Docker Desktop ────────────────────────────────────────────────────────
Write-Step "Docker Desktop"
if (-not (Test-Command "docker")) {
    Write-Host "  Installing Docker Desktop (this may take a few minutes)..." -ForegroundColor Gray
    Install-Winget-Package "Docker.DockerDesktop" "Docker Desktop"
    Write-Warn "Docker Desktop installed. Please START Docker Desktop manually, then re-run this script."
    Write-Warn "Docker requires a system restart or manual launch before continuing."
} else {
    $dv = docker --version
    Write-OK $dv
    # Check daemon is running
    $running = docker info 2>&1 | Select-String "Server Version"
    if (-not $running) {
        Write-Warn "Docker daemon not running. Start Docker Desktop and wait for it to be ready."
    } else {
        Write-OK "Docker daemon running"
    }
}

# ── 6. VS Code (recommended) ─────────────────────────────────────────────────
Write-Step "Visual Studio Code (optional)"
if (-not (Test-Command "code")) {
    $answer = Read-Host "  Install VS Code? (y/n)"
    if ($answer -eq "y") {
        Install-Winget-Package "Microsoft.VisualStudioCode" "VS Code"
        $env:PATH += ";$env:LOCALAPPDATA\Programs\Microsoft VS Code\bin"
        # Install recommended extensions
        code --install-extension ms-python.python
        code --install-extension bradlc.vscode-tailwindcss
        code --install-extension dbaeumer.vscode-eslint
        code --install-extension esbenp.prettier-vscode
        code --install-extension ms-azuretools.vscode-docker
        Write-OK "VS Code + extensions installed"
    }
} else { Write-OK "VS Code already installed" }

# ── 7. Clone / locate repo ────────────────────────────────────────────────────
Write-Step "Project setup"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot
Write-OK "Working directory: $projectRoot"

# ── 8. Copy .env ─────────────────────────────────────────────────────────────
Write-Step "Environment configuration"
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-OK "Created .env from .env.example"
    Write-Warn "IMPORTANT: Open .env and add your API keys before starting the app!"
    Write-Warn "  Required: THE_ODDS_API_KEY (free at the-odds-api.com)"
    Write-Warn "  Optional: DISCORD_WEBHOOK_URL, TELEGRAM_BOT_TOKEN"
} else {
    Write-OK ".env already exists"
}

# ── 9. Install Python dependencies ────────────────────────────────────────────
Write-Step "Python virtual environment + dependencies"
$venvPath = "backend\.venv"
if (-not (Test-Path $venvPath)) {
    python -m venv $venvPath
    Write-OK "Created venv at $venvPath"
}
& "$venvPath\Scripts\Activate.ps1"
pip install --upgrade pip --quiet
pip install -r backend\requirements.txt --quiet
Write-OK "Python dependencies installed"

# Install Playwright browsers
playwright install chromium
Write-OK "Playwright Chromium browser installed"

# ── 10. Install Node dependencies ─────────────────────────────────────────────
Write-Step "Node.js dependencies (frontend)"
Set-Location frontend
npm install --legacy-peer-deps
Set-Location ..
Write-OK "Node dependencies installed"

# ── 11. Summary ───────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "  PropEdge AI — Setup complete!" -ForegroundColor Green
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Next steps:" -ForegroundColor White
Write-Host "  1. Add your API keys to .env"                           -ForegroundColor Gray
Write-Host "  2. Start Docker Desktop (if not already running)"       -ForegroundColor Gray
Write-Host "  3. Run:  docker compose up -d"                          -ForegroundColor Yellow
Write-Host "     — OR for local dev without Docker:"                  -ForegroundColor Gray
Write-Host "       Terminal 1:  cd backend && uvicorn app.main:app --reload" -ForegroundColor Yellow
Write-Host "       Terminal 2:  cd frontend && npm run dev"           -ForegroundColor Yellow
Write-Host ""
Write-Host "  App URLs once running:"
Write-Host "    Frontend:  http://localhost:3000  (or http://localhost via NGINX)" -ForegroundColor Cyan
Write-Host "    API:       http://localhost:8000"                      -ForegroundColor Cyan
Write-Host "    API Docs:  http://localhost:8000/docs"                 -ForegroundColor Cyan
Write-Host ""
