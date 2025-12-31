# Bundle Ollama for Windows distribution
# This script downloads and bundles Ollama into the Aurity Desktop installer

param(
    [string]$Version = "latest"
)

$ErrorActionPreference = "Stop"

$BinDir = Join-Path $PSScriptRoot ".." "src-tauri" "binaries"

Write-Host "=== Bundle Ollama for Windows ===" -ForegroundColor Cyan

# Create binaries directory if needed
if (-not (Test-Path $BinDir)) {
    New-Item -ItemType Directory -Path $BinDir -Force | Out-Null
}

# Determine download URL
if ($Version -eq "latest") {
    $DownloadUrl = "https://ollama.com/download/OllamaSetup.exe"
} else {
    $DownloadUrl = "https://github.com/ollama/ollama/releases/download/v$Version/OllamaSetup.exe"
}

$OutputFile = Join-Path $BinDir "OllamaSetup.exe"

Write-Host "Downloading Ollama from: $DownloadUrl" -ForegroundColor Yellow

# Download Ollama installer
try {
    Invoke-WebRequest -Uri $DownloadUrl -OutFile $OutputFile -UseBasicParsing
    Write-Host "[OK] Downloaded to: $OutputFile" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Failed to download: $_" -ForegroundColor Red
    exit 1
}

# Verify file exists and has size
$FileInfo = Get-Item $OutputFile
Write-Host "File size: $([math]::Round($FileInfo.Length / 1MB, 2)) MB" -ForegroundColor Gray

Write-Host ""
Write-Host "=== Ollama bundled successfully ===" -ForegroundColor Green
Write-Host "The installer will be included in the Aurity Desktop package." -ForegroundColor Gray
