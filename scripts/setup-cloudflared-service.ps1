# ============================================================================
# Setup Cloudflared as Windows Service - AURITY Edition
# ============================================================================
# Configura cloudflared como servicio Windows para exponer Ollama via tunnel
#
# Uso:
#   .\setup-cloudflared-service.ps1                    # Modo quickstart (URL temporal)
#   .\setup-cloudflared-service.ps1 -Hostname ollama.tudominio.com  # Con hostname fijo
#   .\setup-cloudflared-service.ps1 -TunnelName mi-tunnel           # Nombre custom
#   .\setup-cloudflared-service.ps1 -SkipServiceInstall             # Solo configurar
#
# Requiere: Ejecutar como Administrador (para instalar servicio)
# ============================================================================

param(
    [string]$Hostname = "",
    [string]$TunnelName = "aurity-ollama",
    [int]$OllamaPort = 11434,
    [switch]$SkipServiceInstall,
    [switch]$Force
)

$ErrorActionPreference = "Stop"

# Configuracion
$CLOUDFLARED_PATH = "C:\cloudflared\cloudflared.exe"
$CLOUDFLARED_DIR = "C:\cloudflared"
$CONFIG_PATH = "$CLOUDFLARED_DIR\config.yml"
$DOWNLOAD_URL = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"

# Colores
function Write-Step { param($n, $total, $msg) Write-Host "[$n/$total] $msg" -ForegroundColor Cyan }
function Write-OK { param($msg) Write-Host "[OK] $msg" -ForegroundColor Green }
function Write-Warn { param($msg) Write-Host "[!] $msg" -ForegroundColor Yellow }
function Write-Err { param($msg) Write-Host "[X] $msg" -ForegroundColor Red }
function Write-Info { param($msg) Write-Host "    $msg" -ForegroundColor Gray }

# Banner
Write-Host ""
Write-Host "============================================" -ForegroundColor Magenta
Write-Host "  AURITY Cloudflare Tunnel Setup" -ForegroundColor Magenta
Write-Host "  'Un mago nunca llega tarde...'" -ForegroundColor DarkGray
Write-Host "============================================" -ForegroundColor Magenta
Write-Host ""

# ============================================================================
# PASO 1: Descargar cloudflared si no existe
# ============================================================================
Write-Step 1 6 "Verificando cloudflared..."

if (-not (Test-Path $CLOUDFLARED_PATH)) {
    Write-Warn "cloudflared no encontrado. Descargando..."

    New-Item -ItemType Directory -Force -Path $CLOUDFLARED_DIR | Out-Null

    try {
        $ProgressPreference = 'SilentlyContinue'
        Invoke-WebRequest -Uri $DOWNLOAD_URL -OutFile $CLOUDFLARED_PATH -UseBasicParsing
        $ProgressPreference = 'Continue'
        Write-OK "cloudflared descargado"
    } catch {
        Write-Err "Error descargando cloudflared: $_"
        Write-Info "Descarga manual: $DOWNLOAD_URL"
        exit 1
    }
} else {
    Write-OK "cloudflared encontrado"
}

# Mostrar version
$version = & $CLOUDFLARED_PATH --version 2>&1
Write-Info $version

# ============================================================================
# PASO 2: Autenticar con Cloudflare
# ============================================================================
Write-Step 2 6 "Verificando autenticacion..."

$certPath = "$env:USERPROFILE\.cloudflared\cert.pem"
if (-not (Test-Path $certPath)) {
    Write-Warn "No autenticado. Abriendo navegador..."
    Write-Info "Selecciona tu dominio en el navegador que se abrira."
    Write-Host ""

    & $CLOUDFLARED_PATH tunnel login

    if (-not (Test-Path $certPath)) {
        Write-Err "Autenticacion fallida. Ejecuta manualmente:"
        Write-Info "C:\cloudflared\cloudflared.exe tunnel login"
        exit 1
    }
    Write-OK "Autenticado correctamente"
} else {
    Write-OK "Ya autenticado (cert.pem existe)"
}

# ============================================================================
# PASO 3: Crear o verificar tunnel
# ============================================================================
Write-Step 3 6 "Configurando tunnel '$TunnelName'..."

$tunnelsJson = & $CLOUDFLARED_PATH tunnel list --output json 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Err "Error listando tunnels. Verifica autenticacion."
    exit 1
}

$tunnels = $tunnelsJson | ConvertFrom-Json
$existingTunnel = $tunnels | Where-Object { $_.name -eq $TunnelName }

if (-not $existingTunnel) {
    Write-Warn "Tunnel '$TunnelName' no existe. Creando..."
    & $CLOUDFLARED_PATH tunnel create $TunnelName

    if ($LASTEXITCODE -ne 0) {
        Write-Err "Error creando tunnel"
        exit 1
    }

    # Refrescar lista
    $tunnelsJson = & $CLOUDFLARED_PATH tunnel list --output json
    $tunnels = $tunnelsJson | ConvertFrom-Json
    $existingTunnel = $tunnels | Where-Object { $_.name -eq $TunnelName }
}

$TUNNEL_ID = $existingTunnel.id
Write-OK "Tunnel ID: $TUNNEL_ID"

# Copiar credenciales
$userCredFile = "$env:USERPROFILE\.cloudflared\$TUNNEL_ID.json"
$svcCredFile = "$CLOUDFLARED_DIR\$TUNNEL_ID.json"

if (Test-Path $userCredFile) {
    Copy-Item $userCredFile $svcCredFile -Force
    Write-Info "Credenciales copiadas a $CLOUDFLARED_DIR"
}

# ============================================================================
# PASO 4: Crear config.yml
# ============================================================================
Write-Step 4 6 "Generando configuracion..."

if ($Hostname -eq "") {
    # Modo quickstart - sin hostname fijo
    $configContent = @"
# AURITY Cloudflare Tunnel Config
# Generado: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
# Modo: Quickstart (URL temporal)

tunnel: $TUNNEL_ID
credentials-file: $svcCredFile

ingress:
  - service: http://localhost:$OllamaPort

# Para hostname permanente, agrega:
# ingress:
#   - hostname: ollama.tudominio.com
#     service: http://localhost:$OllamaPort
#   - service: http_status:404
"@
    Write-OK "Config quickstart generada"
    Write-Info "El tunnel usara URL temporal *.trycloudflare.com"
} else {
    # Modo con hostname fijo
    $configContent = @"
# AURITY Cloudflare Tunnel Config
# Generado: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
# Hostname: $Hostname

tunnel: $TUNNEL_ID
credentials-file: $svcCredFile

ingress:
  - hostname: $Hostname
    service: http://localhost:$OllamaPort
    originRequest:
      noTLSVerify: true
  - service: http_status:404
"@
    Write-OK "Config con hostname fijo: $Hostname"

    Write-Host ""
    Write-Host "  IMPORTANTE: Agrega este DNS en Cloudflare Dashboard:" -ForegroundColor Yellow
    Write-Host "  +---------+------------------------+---------------------------+" -ForegroundColor DarkGray
    Write-Host "  | Tipo    | Nombre                 | Destino                   |" -ForegroundColor DarkGray
    Write-Host "  +---------+------------------------+---------------------------+" -ForegroundColor DarkGray
    $subdomain = ($Hostname -split '\.')[0]
    Write-Host "  | CNAME   | $subdomain             | $TUNNEL_ID.cfargotunnel.com |" -ForegroundColor White
    Write-Host "  +---------+------------------------+---------------------------+" -ForegroundColor DarkGray
    Write-Host "  Proxy: ON (nube naranja)" -ForegroundColor Yellow
    Write-Host ""
}

$configContent | Out-File -FilePath $CONFIG_PATH -Encoding utf8 -Force
Write-Info "Guardado en: $CONFIG_PATH"

# ============================================================================
# PASO 5: Instalar como servicio Windows
# ============================================================================
if (-not $SkipServiceInstall) {
    Write-Step 5 6 "Instalando servicio Windows..."

    # Verificar permisos de admin
    $isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

    if (-not $isAdmin) {
        Write-Warn "Se requieren permisos de administrador para instalar el servicio."
        Write-Info "Ejecuta este script como Administrador, o usa -SkipServiceInstall"
        Write-Host ""
        Write-Host "  Para ejecutar manualmente:" -ForegroundColor Yellow
        Write-Host "  Start-Process powershell -Verb RunAs -ArgumentList '-File `"$PSCommandPath`"'" -ForegroundColor Gray
        Write-Host ""
    } else {
        # Desinstalar servicio anterior
        $existingService = Get-Service -Name "cloudflared" -ErrorAction SilentlyContinue
        if ($existingService) {
            Write-Info "Removiendo servicio anterior..."
            Stop-Service cloudflared -Force -ErrorAction SilentlyContinue
            & $CLOUDFLARED_PATH service uninstall 2>$null
            Start-Sleep -Seconds 3
        }

        # Instalar servicio
        & $CLOUDFLARED_PATH service install

        if ($LASTEXITCODE -ne 0) {
            Write-Err "Error instalando servicio"
            exit 1
        }

        Start-Sleep -Seconds 2

        # Verificar e iniciar
        $service = Get-Service -Name "cloudflared" -ErrorAction SilentlyContinue
        if ($service) {
            if ($service.Status -ne 'Running') {
                Start-Service cloudflared
                Start-Sleep -Seconds 2
            }
            $service = Get-Service cloudflared
            Write-OK "Servicio instalado y $($service.Status)"
        } else {
            Write-Err "Servicio no se instalo correctamente"
        }
    }
} else {
    Write-Step 5 6 "Saltando instalacion de servicio (-SkipServiceInstall)"
}

# ============================================================================
# PASO 6: Verificar conexion
# ============================================================================
Write-Step 6 6 "Verificando conexion..."

# Verificar que Ollama responde
try {
    $ollamaResponse = Invoke-RestMethod -Uri "http://localhost:$OllamaPort/api/tags" -TimeoutSec 5 -ErrorAction Stop
    Write-OK "Ollama respondiendo en puerto $OllamaPort"
    $models = ($ollamaResponse.models | ForEach-Object { $_.name }) -join ", "
    if ($models) { Write-Info "Modelos: $models" }
} catch {
    Write-Warn "Ollama no responde en puerto $OllamaPort"
    Write-Info "Inicia Ollama: ollama serve"
}

# Si es quickstart, obtener URL temporal
if ($Hostname -eq "") {
    Write-Info "Para ver la URL del tunnel:"
    Write-Info "  C:\cloudflared\cloudflared.exe tunnel run $TunnelName"
}

# ============================================================================
# Resumen final
# ============================================================================
Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "  Setup Completado" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
Write-Host "Comandos utiles:" -ForegroundColor Yellow
Write-Host "  Get-Service cloudflared                    # Estado del servicio" -ForegroundColor Gray
Write-Host "  Restart-Service cloudflared                # Reiniciar" -ForegroundColor Gray
Write-Host "  C:\cloudflared\cloudflared.exe tunnel list # Ver tunnels" -ForegroundColor Gray
Write-Host "  C:\cloudflared\cloudflared.exe tunnel info $TunnelName  # Info del tunnel" -ForegroundColor Gray
Write-Host ""

if ($Hostname -eq "") {
    Write-Host "Para iniciar tunnel manual (quickstart):" -ForegroundColor Yellow
    Write-Host "  C:\cloudflared\cloudflared.exe tunnel --url http://localhost:$OllamaPort" -ForegroundColor Gray
} else {
    Write-Host "El tunnel '$TunnelName' expone:" -ForegroundColor Yellow
    Write-Host "  https://$Hostname -> http://localhost:$OllamaPort" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "El tunnel arrancara automaticamente al reiniciar Windows." -ForegroundColor Green
Write-Host ""
