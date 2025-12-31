<#
.SYNOPSIS
    FI Edge Monitor - AURITY v0.1.1
.DESCRIPTION
    Monitor interactivo para Ollama + Cloudflare Tunnel con:
    - URL completa (no truncada)
    - Ancho dinamico segun terminal
    - Indicador de latencia
    - Modelo activo con tamano
    - Test LLM interactivo
.EXAMPLE
    .\fi-edge-monitor.ps1
    .\fi-edge-monitor.ps1 -RefreshSeconds 3
#>

param(
    [int]$RefreshSeconds = 2
)

$Host.UI.RawUI.WindowTitle = "FI Edge Monitor - AURITY"

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

function Get-TerminalWidth {
    try {
        $width = $Host.UI.RawUI.WindowSize.Width
        if ($width -lt 70) { $width = 70 }
        if ($width -gt 120) { $width = 120 }
        return $width
    } catch {
        return 80
    }
}

function Get-OllamaStatus {
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -TimeoutSec 3 -ErrorAction Stop
        return @{
            Running = $true
            Models = $response.models | ForEach-Object { $_.name }
        }
    } catch {
        return @{
            Running = $false
            Models = @()
        }
    }
}

function Get-ActiveModel {
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:11434/api/ps" -TimeoutSec 3 -ErrorAction Stop
        if ($response.models -and $response.models.Count -gt 0) {
            $model = $response.models[0]
            $sizeGB = [math]::Round($model.size / 1GB, 1)
            return @{
                Name = $model.name
                Size = "$sizeGB GB"
                Status = "loaded"
            }
        }
    } catch {}

    # No model loaded, get first available
    $ollama = Get-OllamaStatus
    if ($ollama.Models.Count -gt 0) {
        return @{
            Name = $ollama.Models[0]
            Size = "?"
            Status = "not loaded"
        }
    }
    return @{
        Name = "none"
        Size = "-"
        Status = "no models"
    }
}

function Get-TunnelUrl {
    $logFiles = @(
        "$env:TEMP\ollama-tunnel-url.txt",
        "$env:TEMP\cf-tunnel.log",
        "$env:TEMP\ollama-tunnel.log",
        "$env:TEMP\ollama-tunnel.log.err"
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
            Running = $true
            PID = $proc.Id
            URL = $url
        }
    } else {
        return @{
            Running = $false
            PID = $null
            URL = $null
        }
    }
}

function Get-TunnelLatency {
    param([string]$url)
    if (-not $url) { return "N/A" }

    try {
        $sw = [System.Diagnostics.Stopwatch]::StartNew()
        $null = Invoke-RestMethod -Uri "$url/api/tags" -TimeoutSec 10 -ErrorAction Stop
        $sw.Stop()
        return "$($sw.ElapsedMilliseconds)ms"
    } catch {
        return "FAIL"
    }
}

function Invoke-LLMTest {
    param([string]$url)

    Clear-Host
    Write-Host ""
    Write-Host "  Running LLM Test..." -ForegroundColor Cyan
    Write-Host ""

    try {
        $body = @{
            model = "qwen3:1.7b"
            messages = @(
                @{ role = "user"; content = "Say hello in 5 words" }
            )
            think = $false
            stream = $false
        } | ConvertTo-Json -Depth 3

        $sw = [System.Diagnostics.Stopwatch]::StartNew()
        $response = Invoke-RestMethod -Uri "$url/api/chat" -Method Post -Body $body -ContentType "application/json" -TimeoutSec 60
        $sw.Stop()

        $content = $response.message.content
        if ($content.Length -gt 100) { $content = $content.Substring(0, 100) + "..." }

        Write-Host "  [OK] " -ForegroundColor Green -NoNewline
        Write-Host "Response in $($sw.ElapsedMilliseconds)ms" -ForegroundColor White
        Write-Host ""
        Write-Host "  $content" -ForegroundColor Gray
    } catch {
        Write-Host "  [FAIL] " -ForegroundColor Red -NoNewline
        Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Gray
    }

    Write-Host ""
    Write-Host "  Press any key to continue..." -ForegroundColor DarkGray
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}

function Copy-TunnelUrl {
    param([string]$url)
    if ($url) {
        Set-Clipboard -Value $url
        return $true
    }
    return $false
}

# ============================================================================
# DRAWING FUNCTIONS
# ============================================================================

function Write-BoxLine {
    param(
        [int]$width,
        [string]$left,
        [string]$fill,
        [string]$right
    )
    Write-Host "$left$($fill * ($width - 2))$right" -ForegroundColor Cyan
}

function Write-PaddedLine {
    param(
        [int]$width,
        [string]$content,
        [int]$contentLen = $content.Length
    )
    $padding = $width - 4 - $contentLen
    if ($padding -lt 0) { $padding = 0 }
    Write-Host -NoNewline (" " * $padding)
    Write-Host " |" -ForegroundColor Cyan
}

# ============================================================================
# MAIN MONITOR DISPLAY
# ============================================================================

function Show-Monitor {
    param([ref]$lastUrl)

    $width = Get-TerminalWidth
    $innerWidth = $width - 4

    # Gather data
    $ollama = Get-OllamaStatus
    $tunnel = Get-TunnelStatus
    $model = Get-ActiveModel
    $time = Get-Date -Format "HH:mm:ss"

    # Get latency (this is the slow part)
    $latency = "..."
    if ($tunnel.URL) {
        $latency = Get-TunnelLatency -url $tunnel.URL
    }

    Clear-Host

    # Top border
    Write-BoxLine -width $width -left "+" -fill "-" -right "+"

    # Header
    $headerLeft = "  FI EDGE MONITOR"
    $headerRight = "AURITY v0.1.1"
    $headerPad = $width - 4 - $headerLeft.Length - $headerRight.Length
    Write-Host -NoNewline "| " -ForegroundColor Cyan
    Write-Host -NoNewline $headerLeft -ForegroundColor Yellow
    Write-Host -NoNewline (" " * $headerPad)
    Write-Host -NoNewline $headerRight -ForegroundColor DarkGray
    Write-Host " |" -ForegroundColor Cyan

    # Header separator
    Write-BoxLine -width $width -left "+" -fill "-" -right "+"

    # OLLAMA line
    Write-Host -NoNewline "|  OLLAMA   " -ForegroundColor Cyan
    if ($ollama.Running) {
        Write-Host -NoNewline "[" -ForegroundColor White
        Write-Host -NoNewline "OK" -ForegroundColor Green
        Write-Host -NoNewline "] Running" -ForegroundColor White
    } else {
        Write-Host -NoNewline "[" -ForegroundColor White
        Write-Host -NoNewline "XX" -ForegroundColor Red
        Write-Host -NoNewline "] Stopped" -ForegroundColor White
    }
    $ollamaInfo = "    localhost:11434"
    Write-Host -NoNewline $ollamaInfo -ForegroundColor DarkGray
    Write-PaddedLine -width $width -content "  OLLAMA   [OK] Running$ollamaInfo" -contentLen (11 + 13 + $ollamaInfo.Length)

    # MODEL line
    $modelDisplay = [string]$model.Name
    if ($modelDisplay.Length -gt 14) { $modelDisplay = $modelDisplay.Substring(0, 11) + "..." }
    $modelInfo = "($($model.Size) $($model.Status))"
    Write-Host -NoNewline "|  MODEL    " -ForegroundColor Cyan
    Write-Host -NoNewline "$modelDisplay".PadRight(14) -ForegroundColor White
    Write-Host -NoNewline $modelInfo -ForegroundColor DarkGray
    Write-PaddedLine -width $width -content "  MODEL    $modelDisplay$modelInfo" -contentLen (11 + 14 + $modelInfo.Length)

    # Empty line
    Write-Host -NoNewline "| " -ForegroundColor Cyan
    Write-Host -NoNewline (" " * ($width - 4))
    Write-Host " |" -ForegroundColor Cyan

    # TUNNEL line
    Write-Host -NoNewline "|  TUNNEL   " -ForegroundColor Cyan
    if ($tunnel.Running) {
        Write-Host -NoNewline "[" -ForegroundColor White
        Write-Host -NoNewline "OK" -ForegroundColor Green
        Write-Host -NoNewline "] Running" -ForegroundColor White
    } else {
        Write-Host -NoNewline "[" -ForegroundColor White
        Write-Host -NoNewline "XX" -ForegroundColor Red
        Write-Host -NoNewline "] Stopped" -ForegroundColor White
    }
    $pidInfo = if ($tunnel.PID) { "    PID: $($tunnel.PID)" } else { "" }
    Write-Host -NoNewline $pidInfo -ForegroundColor DarkGray
    Write-PaddedLine -width $width -content "  TUNNEL   [OK] Running$pidInfo" -contentLen (11 + 13 + $pidInfo.Length)

    # URL line (FULL URL - no truncation if fits)
    Write-Host -NoNewline "|  URL      " -ForegroundColor Cyan
    $maxUrlLen = $innerWidth - 11
    if ($tunnel.URL) {
        $urlDisplay = $tunnel.URL
        if ($urlDisplay.Length -gt $maxUrlLen) {
            $urlDisplay = $urlDisplay.Substring(0, $maxUrlLen - 3) + "..."
        }
        Write-Host -NoNewline $urlDisplay -ForegroundColor Magenta
        $urlPad = $maxUrlLen - $urlDisplay.Length
    } else {
        $noUrl = "(no tunnel active)"
        Write-Host -NoNewline $noUrl -ForegroundColor DarkGray
        $urlPad = $maxUrlLen - $noUrl.Length
    }
    Write-Host -NoNewline (" " * $urlPad)
    Write-Host " |" -ForegroundColor Cyan

    # STATUS line with latency
    Write-Host -NoNewline "|  STATUS   " -ForegroundColor Cyan
    if ($tunnel.URL -and $latency -ne "FAIL") {
        Write-Host -NoNewline "[" -ForegroundColor White
        Write-Host -NoNewline "OK" -ForegroundColor Green
        Write-Host -NoNewline "] Accessible" -ForegroundColor White
        $latencyInfo = "   Latency: $latency"
        Write-Host -NoNewline $latencyInfo -ForegroundColor DarkGray
        $statusLen = 16 + $latencyInfo.Length
    } elseif ($tunnel.URL) {
        Write-Host -NoNewline "[" -ForegroundColor White
        Write-Host -NoNewline "!!" -ForegroundColor Red
        Write-Host -NoNewline "] Unreachable" -ForegroundColor Red
        $statusLen = 17
    } else {
        Write-Host -NoNewline "[" -ForegroundColor White
        Write-Host -NoNewline "--" -ForegroundColor DarkGray
        Write-Host -NoNewline "] N/A" -ForegroundColor DarkGray
        $statusLen = 9
    }
    Write-PaddedLine -width $width -content "  STATUS   [OK] status" -contentLen (11 + $statusLen)

    # Separator
    Write-BoxLine -width $width -left "+" -fill "-" -right "+"

    # Footer with options
    Write-Host -NoNewline "|  " -ForegroundColor Cyan
    Write-Host -NoNewline "[Q]" -ForegroundColor Yellow
    Write-Host -NoNewline " Quit   " -ForegroundColor Gray
    Write-Host -NoNewline "[R]" -ForegroundColor Yellow
    Write-Host -NoNewline " Restart   " -ForegroundColor Gray
    Write-Host -NoNewline "[T]" -ForegroundColor Yellow
    Write-Host -NoNewline " Test LLM   " -ForegroundColor Gray
    Write-Host -NoNewline "[C]" -ForegroundColor Yellow
    Write-Host -NoNewline " Copy URL" -ForegroundColor Gray

    $footerLeft = 3 + 3 + 8 + 3 + 11 + 3 + 12 + 3 + 9  # approximate
    $footerPad = $width - 4 - $footerLeft - $time.Length
    if ($footerPad -lt 1) { $footerPad = 1 }
    Write-Host -NoNewline (" " * $footerPad)
    Write-Host -NoNewline $time -ForegroundColor DarkGray
    Write-Host " |" -ForegroundColor Cyan

    # Bottom border
    Write-BoxLine -width $width -left "+" -fill "-" -right "+"

    $lastUrl.Value = $tunnel.URL
}

# ============================================================================
# MAIN LOOP
# ============================================================================

$lastUrl = $null

# Hide cursor
try { [Console]::CursorVisible = $false } catch {}

try {
    while ($true) {
        Show-Monitor -lastUrl ([ref]$lastUrl)

        $timeout = [DateTime]::Now.AddSeconds($RefreshSeconds)
        while ([DateTime]::Now -lt $timeout) {
            if ([Console]::KeyAvailable) {
                $key = [Console]::ReadKey($true)
                switch ($key.Key) {
                    'Q' {
                        Clear-Host
                        Write-Host ""
                        Write-Host "  FI Edge Monitor stopped." -ForegroundColor Cyan
                        Write-Host ""
                        exit 0
                    }
                    'R' {
                        Clear-Host
                        Write-Host ""
                        Write-Host "  Restarting tunnel..." -ForegroundColor Yellow
                        Get-Process cloudflared -ErrorAction SilentlyContinue | Stop-Process -Force
                        Start-Sleep 2

                        $cfPath = "C:\cloudflared\cloudflared.exe"
                        if (Test-Path $cfPath) {
                            Start-Process -FilePath $cfPath -ArgumentList "tunnel --url http://localhost:11434" -RedirectStandardError "$env:TEMP\ollama-tunnel.log.err" -WindowStyle Hidden
                            Write-Host "  Tunnel restarting... please wait" -ForegroundColor Gray
                            Start-Sleep 5
                        } else {
                            Write-Host "  cloudflared not found at $cfPath" -ForegroundColor Red
                            Start-Sleep 2
                        }
                    }
                    'T' {
                        if ($lastUrl) {
                            Invoke-LLMTest -url $lastUrl
                        } else {
                            Clear-Host
                            Write-Host ""
                            Write-Host "  No tunnel URL available for testing" -ForegroundColor Red
                            Write-Host ""
                            Write-Host "  Press any key to continue..." -ForegroundColor DarkGray
                            $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
                        }
                    }
                    'C' {
                        if (Copy-TunnelUrl -url $lastUrl) {
                            # Brief visual feedback
                            Write-Host ""
                            Write-Host "  URL copied to clipboard!" -ForegroundColor Green
                            Start-Sleep -Milliseconds 500
                        }
                    }
                }
            }
            Start-Sleep -Milliseconds 100
        }
    }
} finally {
    # Restore cursor
    try { [Console]::CursorVisible = $true } catch {}
}
