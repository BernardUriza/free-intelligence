# ============================================================================
# AURITY Ollama Tunnel Manager (Windows)
# ============================================================================
# Inicia Cloudflare Tunnel para exponer Ollama local y actualiza DO backend
#
# Uso:
#   .\ollama-tunnel.ps1 start    # Inicia tunnel y actualiza DO
#   .\ollama-tunnel.ps1 stop     # Detiene tunnel
#   .\ollama-tunnel.ps1 status   # Muestra estado actual
# ============================================================================

param(
    [Parameter(Position=0)]
    [ValidateSet("start", "stop", "status", "url", "restart")]
    [string]$Action = "start"
)

$ErrorActionPreference = "Stop"

# Configuración
$TUNNEL_LOG = "$env:TEMP\ollama-tunnel.log"
$TUNNEL_URL_FILE = "$env:TEMP\ollama-tunnel-url.txt"
$TUNNEL_PID_FILE = "$env:TEMP\ollama-tunnel.pid"
$DO_HOST = "root@104.131.175.65"
$OLLAMA_PORT = "11434"
$CLOUDFLARED_PATH = "C:\cloudflared\cloudflared.exe"

function Write-Log { param($msg) Write-Host "[TUNNEL] $msg" -ForegroundColor Blue }
function Write-Success { param($msg) Write-Host "[OK] $msg" -ForegroundColor Green }
function Write-Warn { param($msg) Write-Host "[!] $msg" -ForegroundColor Yellow }
function Write-Err { param($msg) Write-Host "[X] $msg" -ForegroundColor Red }

function Test-Ollama {
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:$OLLAMA_PORT/api/tags" -TimeoutSec 5
        return $true
    } catch {
        return $false
    }
}

function Start-OllamaService {
    Write-Log "Verificando Ollama..."

    if (Test-Ollama) {
        Write-Success "Ollama ya está corriendo"
        return
    }

    Write-Log "Iniciando Ollama..."
    $env:OLLAMA_ORIGINS = "*"
    $env:OLLAMA_HOST = "0.0.0.0:$OLLAMA_PORT"

    # Buscar ollama
    $ollamaPath = Get-Command ollama -ErrorAction SilentlyContinue
    if (-not $ollamaPath) {
        Write-Err "Ollama no encontrado. Instalar desde https://ollama.ai"
        exit 1
    }

    Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden
    Start-Sleep -Seconds 5

    if (Test-Ollama) {
        Write-Success "Ollama iniciado"
    } else {
        Write-Err "No se pudo iniciar Ollama"
        exit 1
    }
}

function Start-FIEdgeServer {
    Write-Log "Verificando FI Edge Server..."

    # Verificar si ya está corriendo
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:9200/health" -TimeoutSec 3
        Write-Success "FI Edge Server ya está corriendo"
        return
    } catch {}

    Write-Log "Iniciando FI Edge Server..."

    # Buscar python
    $pythonPath = Get-Command python -ErrorAction SilentlyContinue
    if (-not $pythonPath) {
        $pythonPath = Get-Command python3 -ErrorAction SilentlyContinue
    }
    if (-not $pythonPath) {
        Write-Warn "Python no encontrado, FI Edge Server no iniciado"
        return
    }

    # Iniciar FI Edge Server
    $fiPath = Split-Path -Parent $PSScriptRoot
    $env:PYTHONPATH = "$fiPath\backend\src"
    Start-Process -FilePath $pythonPath.Source -ArgumentList "-m fi_edge.server" -WorkingDirectory $fiPath -WindowStyle Hidden
    Start-Sleep -Seconds 3

    # Verificar
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:9200/health" -TimeoutSec 5
        Write-Success "FI Edge Server iniciado (puerto 9200)"
    } catch {
        Write-Warn "FI Edge Server pudo no haber iniciado correctamente"
    }
}

function Stop-FIEdgeServer {
    Write-Log "Deteniendo FI Edge Server..."
    Get-Process -Name "python*" -ErrorAction SilentlyContinue | Where-Object {
        $_.CommandLine -like "*fi_edge.server*"
    } | Stop-Process -Force -ErrorAction SilentlyContinue
    Write-Success "FI Edge Server detenido"
}

function Start-Tunnel {
    Write-Log "Iniciando Cloudflare Tunnel..."

    # Verificar cloudflared
    if (-not (Test-Path $CLOUDFLARED_PATH)) {
        Write-Err "cloudflared no encontrado en $CLOUDFLARED_PATH"
        Write-Log "Descarga: https://github.com/cloudflare/cloudflared/releases"
        exit 1
    }

    # Matar tunnel anterior
    Get-Process -Name "cloudflared" -ErrorAction SilentlyContinue | Stop-Process -Force
    Start-Sleep -Seconds 2

    # Iniciar tunnel (quickstart con trycloudflare)
    $tunnelProcess = Start-Process -FilePath $CLOUDFLARED_PATH -ArgumentList "tunnel --url http://localhost:$OLLAMA_PORT" -PassThru -RedirectStandardOutput $TUNNEL_LOG -RedirectStandardError "$TUNNEL_LOG.err" -WindowStyle Hidden
    $tunnelProcess.Id | Out-File -FilePath $TUNNEL_PID_FILE

    Write-Log "Esperando URL del tunnel (PID: $($tunnelProcess.Id))..."

    # Esperar hasta 30 segundos por la URL
    for ($i = 1; $i -le 30; $i++) {
        Start-Sleep -Seconds 1

        # Buscar URL en stderr (cloudflared escribe ahí)
        if (Test-Path "$TUNNEL_LOG.err") {
            $content = Get-Content "$TUNNEL_LOG.err" -Raw -ErrorAction SilentlyContinue
            if ($content -match "(https://[a-zA-Z0-9-]+\.trycloudflare\.com)") {
                $tunnelUrl = $matches[1]
                $tunnelUrl | Out-File -FilePath $TUNNEL_URL_FILE
                Write-Success "Tunnel activo: $tunnelUrl"
                return $tunnelUrl
            }
        }
    }

    Write-Err "Timeout esperando URL del tunnel"
    if (Test-Path "$TUNNEL_LOG.err") { Get-Content "$TUNNEL_LOG.err" }
    exit 1
}

function Update-DigitalOcean {
    param([string]$url)

    Write-Log "Actualizando Digital Ocean backend..."

    # Verificar SSH
    $sshTest = ssh -o ConnectTimeout=10 -o BatchMode=yes $DO_HOST "echo ok" 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Err "No se puede conectar a DO via SSH"
        Write-Warn "Ejecuta manualmente en DO: export OLLAMA_HOST=$url && reiniciar backend"
        return
    }

    # Script para ejecutar en DO
    $remoteScript = @"
pkill -9 -f uvicorn 2>/dev/null || true
sleep 2
cd /opt/free-intelligence
export PYTHONPATH=.
export PYTHONNOUSERSITE=1
export OLLAMA_HOST="$url"
echo "$url" > /tmp/ollama-tunnel-url.txt
nohup python3.14 -m uvicorn backend.app.main:app --host 0.0.0.0 --port 7001 > /tmp/backend.log 2>&1 &
sleep 10
curl -s http://localhost:7001/api/health
"@

    $result = $remoteScript | ssh $DO_HOST "bash"
    Write-Success "DO actualizado con OLLAMA_HOST=$url"
}

function Test-Connection {
    param([string]$url)

    Write-Log "Probando conexión..."

    try {
        $response = Invoke-RestMethod -Uri "$url/api/tags" -TimeoutSec 10
        Write-Success "Tunnel -> Ollama: OK"
        Write-Host "  Modelos: $($response.models.name -join ', ')" -ForegroundColor Gray
    } catch {
        Write-Err "Tunnel -> Ollama: FAILED"
    }
}

function Stop-Tunnel {
    Write-Log "Deteniendo tunnel..."
    Get-Process -Name "cloudflared" -ErrorAction SilentlyContinue | Stop-Process -Force
    Remove-Item -Path $TUNNEL_PID_FILE, $TUNNEL_URL_FILE -Force -ErrorAction SilentlyContinue
    Write-Success "Tunnel detenido"
}

function Show-Status {
    Write-Host ""
    Write-Host "=== AURITY Ollama Tunnel Status (Windows) ===" -ForegroundColor Cyan
    Write-Host ""

    # Ollama
    if (Test-Ollama) {
        Write-Host "Ollama:       " -NoNewline; Write-Host "Running" -ForegroundColor Green -NoNewline; Write-Host " (localhost:$OLLAMA_PORT)"
    } else {
        Write-Host "Ollama:       " -NoNewline; Write-Host "Stopped" -ForegroundColor Red
    }

    # FI Edge Server
    try {
        $response = Invoke-RestMethod -Uri "http://localhost:9200/health" -TimeoutSec 3
        Write-Host "FI Edge:      " -NoNewline; Write-Host "Running" -ForegroundColor Green -NoNewline; Write-Host " (localhost:9200)"
    } catch {
        Write-Host "FI Edge:      " -NoNewline; Write-Host "Stopped" -ForegroundColor Red
    }

    # Tunnel
    $tunnelProc = Get-Process -Name "cloudflared" -ErrorAction SilentlyContinue
    if ($tunnelProc) {
        if (Test-Path $TUNNEL_URL_FILE) {
            $url = Get-Content $TUNNEL_URL_FILE
            Write-Host "Tunnel:       " -NoNewline; Write-Host "Running" -ForegroundColor Green -NoNewline; Write-Host " ($url)"
        } else {
            Write-Host "Tunnel:       " -NoNewline; Write-Host "Running" -ForegroundColor Yellow -NoNewline; Write-Host " (URL desconocida)"
        }
    } else {
        Write-Host "Tunnel:       " -NoNewline; Write-Host "Stopped" -ForegroundColor Red
    }

    # DO Backend
    try {
        $health = Invoke-RestMethod -Uri "https://app.aurity.io/api/health" -TimeoutSec 5
        Write-Host "DO Backend:   " -NoNewline; Write-Host "Running" -ForegroundColor Green
    } catch {
        Write-Host "DO Backend:   " -NoNewline; Write-Host "Not responding" -ForegroundColor Red
    }

    Write-Host ""
}

function Show-Url {
    if (Test-Path $TUNNEL_URL_FILE) {
        Get-Content $TUNNEL_URL_FILE
    } else {
        Write-Err "No hay tunnel activo"
        exit 1
    }
}

# Main
switch ($Action) {
    "start" {
        Start-OllamaService
        Start-FIEdgeServer
        $url = Start-Tunnel
        Update-DigitalOcean -url $url
        Test-Connection -url $url
        Write-Host ""
        Write-Success "=== Tunnel configurado ==="
        Write-Host "URL: $url"
        Write-Host "FI Edge: http://localhost:9200"
        Write-Host "Monitor: http://localhost:9200 (o apps/fi-monitor)"
        Write-Host ""
        Write-Host "Para monitorear: Get-Content $TUNNEL_LOG -Wait"
        Write-Host "Para detener:    .\ollama-tunnel.ps1 stop"
    }
    "stop" {
        Stop-Tunnel
        Stop-FIEdgeServer
    }
    "status" {
        Show-Status
    }
    "url" {
        Show-Url
    }
    "restart" {
        Stop-Tunnel
        Start-Sleep -Seconds 2
        & $PSCommandPath start
    }
}
