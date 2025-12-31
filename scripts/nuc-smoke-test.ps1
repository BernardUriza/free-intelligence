# ============================================================================
# NUC Always-On Smoke Test (Windows)
# ============================================================================
# Verificar que todos los servicios están UP después de reinicio
# ============================================================================

$ErrorActionPreference = "Continue"

function Test-Endpoint {
    param([string]$Name, [string]$Url)

    try {
        $response = Invoke-WebRequest -Uri $Url -TimeoutSec 10 -UseBasicParsing
        if ($response.StatusCode -eq 200) {
            Write-Host "[OK] $Name" -ForegroundColor Green
            Write-Host "     $Url" -ForegroundColor Gray
            return $true
        }
    } catch {
        Write-Host "[FAIL] $Name" -ForegroundColor Red
        Write-Host "     $Url - $($_.Exception.Message)" -ForegroundColor Gray
        return $false
    }
    return $false
}

function Test-Service {
    param([string]$Name)

    $svc = Get-Service -Name $Name -ErrorAction SilentlyContinue
    if ($svc -and $svc.Status -eq 'Running') {
        Write-Host "[OK] Service '$Name' Running" -ForegroundColor Green
        return $true
    } else {
        Write-Host "[FAIL] Service '$Name' not running" -ForegroundColor Red
        return $false
    }
}

function Test-Process {
    param([string]$Name)

    $proc = Get-Process -Name $Name -ErrorAction SilentlyContinue
    if ($proc) {
        Write-Host "[OK] Process '$Name' Running (PID: $($proc.Id))" -ForegroundColor Green
        return $true
    } else {
        Write-Host "[FAIL] Process '$Name' not found" -ForegroundColor Red
        return $false
    }
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " NUC Always-On Smoke Test" -ForegroundColor Cyan
Write-Host " $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$results = @()

# 1. Servicios Windows
Write-Host "--- Windows Services ---" -ForegroundColor Yellow
$results += Test-Service "cloudflared"

# 2. Procesos
Write-Host ""
Write-Host "--- Processes ---" -ForegroundColor Yellow
$results += Test-Process "ollama"
$results += Test-Process "cloudflared"

# 3. Endpoints locales
Write-Host ""
Write-Host "--- Local Endpoints ---" -ForegroundColor Yellow
$results += Test-Endpoint "Ollama API" "http://localhost:11434/api/tags"
$results += Test-Endpoint "FI Backend (si corre)" "http://localhost:7001/api/health"

# 4. Tunnel URL
Write-Host ""
Write-Host "--- Cloudflare Tunnel ---" -ForegroundColor Yellow
$tunnelUrlFile = "$env:TEMP\ollama-tunnel-url.txt"
if (Test-Path $tunnelUrlFile) {
    $tunnelUrl = Get-Content $tunnelUrlFile
    Write-Host "[INFO] Tunnel URL: $tunnelUrl" -ForegroundColor Blue
    $results += Test-Endpoint "Tunnel -> Ollama" "$tunnelUrl/api/tags"
} else {
    Write-Host "[WARN] No tunnel URL file found" -ForegroundColor Yellow
}

# 5. DO Backend
Write-Host ""
Write-Host "--- Remote (DO Backend) ---" -ForegroundColor Yellow
$results += Test-Endpoint "app.aurity.io" "https://app.aurity.io/api/health"

# 6. DNS
Write-Host ""
Write-Host "--- Network ---" -ForegroundColor Yellow
try {
    $dns = Resolve-DnsName "cloudflare.com" -ErrorAction Stop
    Write-Host "[OK] DNS resolution working" -ForegroundColor Green
    $results += $true
} catch {
    Write-Host "[FAIL] DNS resolution failed" -ForegroundColor Red
    $results += $false
}

# Resumen
$passed = ($results | Where-Object { $_ -eq $true }).Count
$total = $results.Count

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
if ($passed -eq $total) {
    Write-Host " Results: $passed/$total PASSED" -ForegroundColor Green
} else {
    Write-Host " Results: $passed/$total passed" -ForegroundColor Yellow
}
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

if ($passed -eq $total) {
    Write-Host "All systems operational!" -ForegroundColor Green
} else {
    Write-Host "Some checks failed. Review above." -ForegroundColor Yellow
}
