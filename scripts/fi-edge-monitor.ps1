<#
.SYNOPSIS
    FI Edge Monitor - AURITY
.DESCRIPTION
    Monitor simple para Ollama + Cloudflare Tunnel
.EXAMPLE
    .\fi-edge-monitor.ps1
#>

param(
    [int]$RefreshSeconds = 5
)

$Host.UI.RawUI.WindowTitle = "FI Edge Monitor"

function Get-OllamaStatus {
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -TimeoutSec 3 -ErrorAction Stop
        return @{
            Status = "Running"
            Models = $response.models | ForEach-Object { $_.name }
            Color = "Green"
        }
    } catch {
        return @{
            Status = "Stopped"
            Models = @()
            Color = "Red"
        }
    }
}

function Get-TunnelUrl {
    $logFiles = @(
        "$env:TEMP\cf-tunnel.log",
        "$env:TEMP\ollama-tunnel.log",
        "$env:TEMP\ollama-tunnel-url.txt",
        "C:\Users\buo45\AppData\Local\Temp\cf-tunnel.log"
    )

    foreach ($file in $logFiles) {
        if (Test-Path $file) {
            $content = Get-Content $file -Raw -ErrorAction SilentlyContinue
            if ($content -match "(https://[a-z0-9-]+\.trycloudflare\.com)") {
                return $matches[1]
            }
        }
    }
    return $null
}

function Get-TunnelStatus {
    $proc = Get-Process -Name "cloudflared" -ErrorAction SilentlyContinue
    $url = Get-TunnelUrl

    if ($proc) {
        return @{
            Status = "Running"
            PID = $proc.Id
            URL = $url
            Color = "Green"
        }
    } else {
        return @{
            Status = "Stopped"
            PID = $null
            URL = $null
            Color = "Red"
        }
    }
}

function Test-TunnelConnection {
    param([string]$url)
    if (-not $url) { return $false }
    try {
        $null = Invoke-RestMethod -Uri "$url/api/tags" -TimeoutSec 5 -ErrorAction Stop
        return $true
    } catch {
        return $false
    }
}

function Show-Monitor {
    Clear-Host

    $ollama = Get-OllamaStatus
    $tunnel = Get-TunnelStatus
    $tunnelOk = if ($tunnel.URL) { Test-TunnelConnection $tunnel.URL } else { $false }
    $time = Get-Date -Format "HH:mm:ss"

    Write-Host ""
    Write-Host "  +--------------------------------------------------------------+" -ForegroundColor Cyan
    Write-Host "  |           " -ForegroundColor Cyan -NoNewline
    Write-Host "FI EDGE MONITOR" -ForegroundColor Yellow -NoNewline
    Write-Host "  -  AURITY                    |" -ForegroundColor Cyan
    Write-Host "  +--------------------------------------------------------------+" -ForegroundColor Cyan
    Write-Host "  |                                                              |" -ForegroundColor Cyan

    # Ollama Status
    Write-Host "  |  " -ForegroundColor Cyan -NoNewline
    Write-Host "OLLAMA" -ForegroundColor White -NoNewline
    Write-Host "      " -NoNewline
    if ($ollama.Status -eq "Running") {
        Write-Host "[OK]" -ForegroundColor Green -NoNewline
        Write-Host " Running" -ForegroundColor Green -NoNewline
    } else {
        Write-Host "[XX]" -ForegroundColor Red -NoNewline
        Write-Host " Stopped" -ForegroundColor Red -NoNewline
    }
    Write-Host "     localhost:11434                   |" -ForegroundColor Gray

    # Models
    Write-Host "  |  " -ForegroundColor Cyan -NoNewline
    Write-Host "Models" -ForegroundColor White -NoNewline
    Write-Host "      " -NoNewline
    if ($ollama.Models.Count -gt 0) {
        $modelStr = ($ollama.Models -join ", ")
        if ($modelStr.Length -gt 40) { $modelStr = $modelStr.Substring(0,37) + "..." }
        $padded = $modelStr.PadRight(44)
        Write-Host $padded -ForegroundColor Cyan -NoNewline
    } else {
        Write-Host "(none)".PadRight(44) -ForegroundColor DarkGray -NoNewline
    }
    Write-Host "|" -ForegroundColor Cyan

    Write-Host "  |                                                              |" -ForegroundColor Cyan

    # Tunnel Status
    Write-Host "  |  " -ForegroundColor Cyan -NoNewline
    Write-Host "TUNNEL" -ForegroundColor White -NoNewline
    Write-Host "      " -NoNewline
    if ($tunnel.Status -eq "Running") {
        Write-Host "[OK]" -ForegroundColor Green -NoNewline
        Write-Host " Running" -ForegroundColor Green -NoNewline
        $pidStr = "     PID: $($tunnel.PID)"
        Write-Host $pidStr.PadRight(36) -ForegroundColor Gray -NoNewline
    } else {
        Write-Host "[XX]" -ForegroundColor Red -NoNewline
        Write-Host " Stopped" -ForegroundColor Red -NoNewline
        Write-Host "".PadRight(36) -NoNewline
    }
    Write-Host "|" -ForegroundColor Cyan

    # Tunnel URL
    Write-Host "  |  " -ForegroundColor Cyan -NoNewline
    Write-Host "URL" -ForegroundColor White -NoNewline
    Write-Host "         " -NoNewline
    if ($tunnel.URL) {
        $shortUrl = $tunnel.URL -replace "https://", ""
        if ($shortUrl.Length -gt 42) { $shortUrl = $shortUrl.Substring(0,39) + "..." }
        Write-Host $shortUrl.PadRight(43) -ForegroundColor Magenta -NoNewline
    } else {
        Write-Host "(no tunnel active)".PadRight(43) -ForegroundColor DarkGray -NoNewline
    }
    Write-Host "|" -ForegroundColor Cyan

    # Connection test
    Write-Host "  |  " -ForegroundColor Cyan -NoNewline
    Write-Host "External" -ForegroundColor White -NoNewline
    Write-Host "    " -NoNewline
    if ($tunnelOk) {
        Write-Host "[OK]" -ForegroundColor Green -NoNewline
        Write-Host " Accessible from internet".PadRight(40) -ForegroundColor Green -NoNewline
    } elseif ($tunnel.URL) {
        Write-Host "[..]" -ForegroundColor Yellow -NoNewline
        Write-Host " Checking connection...".PadRight(40) -ForegroundColor Yellow -NoNewline
    } else {
        Write-Host "[--]" -ForegroundColor DarkGray -NoNewline
        Write-Host " N/A".PadRight(40) -ForegroundColor DarkGray -NoNewline
    }
    Write-Host "|" -ForegroundColor Cyan

    Write-Host "  |                                                              |" -ForegroundColor Cyan
    Write-Host "  +--------------------------------------------------------------+" -ForegroundColor Cyan
    Write-Host "  |  " -ForegroundColor Cyan -NoNewline
    Write-Host "[Q]" -ForegroundColor Yellow -NoNewline
    Write-Host " Quit  " -ForegroundColor Gray -NoNewline
    Write-Host "[R]" -ForegroundColor Yellow -NoNewline
    Write-Host " Restart Tunnel  " -ForegroundColor Gray -NoNewline
    Write-Host "[C]" -ForegroundColor Yellow -NoNewline
    Write-Host " Copy URL" -ForegroundColor Gray -NoNewline
    Write-Host "   $time" -ForegroundColor DarkGray -NoNewline
    Write-Host " |" -ForegroundColor Cyan
    Write-Host "  +--------------------------------------------------------------+" -ForegroundColor Cyan
    Write-Host ""

    return $tunnel.URL
}

# Main loop
$lastUrl = $null
Write-Host "Starting FI Edge Monitor... Press Q to quit" -ForegroundColor Gray
Start-Sleep 1

while ($true) {
    $lastUrl = Show-Monitor

    $timeout = [DateTime]::Now.AddSeconds($RefreshSeconds)
    while ([DateTime]::Now -lt $timeout) {
        if ([Console]::KeyAvailable) {
            $key = [Console]::ReadKey($true)
            switch ($key.Key) {
                'Q' {
                    Write-Host ""
                    Write-Host "  Goodbye! " -ForegroundColor Cyan
                    exit 0
                }
                'R' {
                    Write-Host ""
                    Write-Host "  Restarting tunnel..." -ForegroundColor Yellow
                    Get-Process cloudflared -ErrorAction SilentlyContinue | Stop-Process -Force
                    Start-Sleep 2
                    Start-Process -FilePath "C:\cloudflared\cloudflared.exe" -ArgumentList "tunnel --url http://localhost:11434" -RedirectStandardError "$env:TEMP\cf-tunnel.log" -WindowStyle Hidden
                    Start-Sleep 5
                }
                'C' {
                    if ($lastUrl) {
                        Set-Clipboard -Value $lastUrl
                        Write-Host ""
                        Write-Host "  URL copied to clipboard!" -ForegroundColor Green
                        Start-Sleep 1
                    }
                }
            }
        }
        Start-Sleep -Milliseconds 100
    }
}
