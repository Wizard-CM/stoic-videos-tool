# ToonForge setup for Windows (PowerShell)
# Prerequisites: Python 3.11, Node.js, and internet access
# Run as: Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
#         .\scripts\setup_windows.ps1

$ErrorActionPreference = "Stop"

$REPO_ROOT = Split-Path -Parent $PSScriptRoot
$BACKEND_DIR = Join-Path $REPO_ROOT "backend"
$FRONTEND_DIR = Join-Path $REPO_ROOT "frontend"
$VENDOR_DIR = Join-Path $REPO_ROOT "vendor"
$FFMPEG_DIR = Join-Path $VENDOR_DIR "ffmpeg"
$RHUBARB_DIR = Join-Path $VENDOR_DIR "rhubarb"
$VOICES_DIR = Join-Path $VENDOR_DIR "piper_voices"

Write-Host "ToonForge Windows Setup" -ForegroundColor Green

# Check Python 3.11
Write-Host "`nChecking Python 3.11..."
$python = py -3.11 --version 2>$null
if (-not $python) {
    Write-Host "ERROR: Python 3.11 not found. Install from https://www.python.org/" -ForegroundColor Red
    exit 1
}
Write-Host "Found: $python"

# Create venv
Write-Host "`nSetting up Python virtual environment..."
if (Test-Path (Join-Path $BACKEND_DIR ".venv")) {
    Write-Host "  venv already exists, skipping."
} else {
    py -3.11 -m venv (Join-Path $BACKEND_DIR ".venv")
    Write-Host "  venv created."
}

# Install dependencies
Write-Host "`nInstalling Python dependencies..."
$pip = Join-Path $BACKEND_DIR ".venv\Scripts\pip.exe"
& $pip install -q -r (Join-Path $BACKEND_DIR "requirements.txt")
Write-Host "  requirements.txt installed."

# Download FFmpeg if not present
Write-Host "`nSetting up FFmpeg..."
$ffmpeg_exe = Join-Path $FFMPEG_DIR "ffmpeg.exe"
$ffprobe_exe = Join-Path $FFMPEG_DIR "ffprobe.exe"

if ((Test-Path $ffmpeg_exe) -and (Test-Path $ffprobe_exe)) {
    Write-Host "  FFmpeg already downloaded, skipping."
} else {
    Write-Host "  Downloading FFmpeg essentials..."
    $zip_file = Join-Path $env:TEMP "ffmpeg.zip"
    Invoke-WebRequest -Uri "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip" `
        -OutFile $zip_file -ErrorAction Stop

    if (-not (Test-Path $FFMPEG_DIR)) { New-Item -ItemType Directory -Path $FFMPEG_DIR -Force | Out-Null }

    Add-Type -AssemblyName System.IO.Compression.FileSystem
    [System.IO.Compression.ZipFile]::ExtractToDirectory($zip_file, $FFMPEG_DIR)

    # Extract ffmpeg.exe and ffprobe.exe from the nested folder
    $extracted = Get-ChildItem -Path $FFMPEG_DIR -Directory -Recurse | Where-Object { $_.Name -match "ffmpeg" } | Select-Object -First 1
    if ($extracted) {
        Copy-Item (Join-Path $extracted.FullName "bin\ffmpeg.exe") $ffmpeg_exe -Force
        Copy-Item (Join-Path $extracted.FullName "bin\ffprobe.exe") $ffprobe_exe -Force
        Remove-Item (Join-Path $FFMPEG_DIR (Split-Path $extracted -Leaf)) -Recurse -Force
    }

    Remove-Item $zip_file -Force
    Write-Host "  FFmpeg downloaded to $FFMPEG_DIR"
}

# Download Rhubarb if not present
Write-Host "`nSetting up Rhubarb Lip Sync..."
$rhubarb_exe = Join-Path $RHUBARB_DIR "rhubarb.exe"

if (Test-Path $rhubarb_exe) {
    Write-Host "  Rhubarb already downloaded, skipping."
} else {
    Write-Host "  Downloading Rhubarb 1.14.0..."
    $zip_file = Join-Path $env:TEMP "rhubarb.zip"
    Invoke-WebRequest -Uri "https://github.com/DanielSWolf/rhubarb-lip-sync/releases/download/v1.14.0/Rhubarb-Lip-Sync-1.14.0-Windows.zip" `
        -OutFile $zip_file -ErrorAction Stop

    if (Test-Path $RHUBARB_DIR) { Remove-Item $RHUBARB_DIR -Recurse -Force }
    New-Item -ItemType Directory -Path $RHUBARB_DIR -Force | Out-Null

    Add-Type -AssemblyName System.IO.Compression.FileSystem
    [System.IO.Compression.ZipFile]::ExtractToDirectory($zip_file, $RHUBARB_DIR)

    Remove-Item $zip_file -Force
    Write-Host "  Rhubarb downloaded to $RHUBARB_DIR"
}

# Download Piper voices
Write-Host "`nSetting up Piper voices..."
if (-not (Test-Path $VOICES_DIR)) { New-Item -ItemType Directory -Path $VOICES_DIR -Force | Out-Null }

$voices = @(
    "en_US-ryan-medium",
    "en_US-joe-medium",
    "en_US-john-medium",
    "en_US-norman-medium",
    "en_US-amy-medium",
    "en_US-kristin-medium",
    "en_US-hfc_female-medium",
    "en_US-kathleen-low"
)

foreach ($voice in $voices) {
    $onnx_file = Join-Path $VOICES_DIR "$voice.onnx"
    $json_file = Join-Path $VOICES_DIR "$voice.onnx.json"

    if ((Test-Path $onnx_file) -and (Test-Path $json_file)) {
        Write-Host "  $voice already downloaded, skipping."
    } else {
        Write-Host "  Downloading $voice..."
        $base_url = "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US"

        # Determine quality (most voices are medium, kathleen-low is special)
        $quality = if ($voice -like "*kathleen*") { "low" } else { "medium" }

        Invoke-WebRequest -Uri "$base_url/$voice/$quality/$voice.onnx" `
            -OutFile $onnx_file -ErrorAction Stop
        Invoke-WebRequest -Uri "$base_url/$voice/$quality/$voice.onnx.json" `
            -OutFile $json_file -ErrorAction Stop
    }
}
Write-Host "  All voices ready in $VOICES_DIR"

# Check Node.js
Write-Host "`nChecking Node.js..."
$node = node --version 2>$null
if (-not $node) {
    Write-Host "  WARNING: Node.js not found. Install from https://nodejs.org/" -ForegroundColor Yellow
    Write-Host "  After installing Node, run from the repo root:"
    Write-Host "    cd frontend && npm ci && npm run build"
} else {
    Write-Host "  Found: $node"

    # Install and build frontend
    Write-Host "`nBuilding frontend..."
    Push-Location $FRONTEND_DIR
    npm ci --silent
    npm run build --silent
    Pop-Location
    Write-Host "  Frontend built successfully."
}

Write-Host "`nSetup complete!" -ForegroundColor Green
Write-Host "To start the dev servers, run: .\scripts\start.bat" -ForegroundColor Cyan
