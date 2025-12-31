# ============================================================================
# Setup Ollama Auto-Start (Windows Task Scheduler)
# ============================================================================
# Ejecutar como Administrador
# Configura Ollama para iniciar al boot con CORS habilitado
# ============================================================================

#Requires -RunAsAdministrator

$ErrorActionPreference = "Stop"

$OLLAMA_PATH = "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe"
$TASK_NAME = "OllamaServe"

Write-Host "=== Ollama Auto-Start Setup ===" -ForegroundColor Cyan
Write-Host ""

# 1. Verificar Ollama
if (-not (Test-Path $OLLAMA_PATH)) {
    # Buscar en PATH
    $ollamaCmd = Get-Command ollama -ErrorAction SilentlyContinue
    if ($ollamaCmd) {
        $OLLAMA_PATH = $ollamaCmd.Source
    } else {
        Write-Host "[FAIL] Ollama no encontrado" -ForegroundColor Red
        Write-Host "       Instalar desde: https://ollama.ai" -ForegroundColor Gray
        exit 1
    }
}
Write-Host "[OK] Ollama: $OLLAMA_PATH" -ForegroundColor Green

# 2. Crear script wrapper que configura CORS
$wrapperScript = @"
@echo off
set OLLAMA_ORIGINS=*
set OLLAMA_HOST=0.0.0.0:11434
"$OLLAMA_PATH" serve
"@

$wrapperPath = "C:\cloudflared\start-ollama.bat"
New-Item -ItemType Directory -Force -Path "C:\cloudflared" | Out-Null
$wrapperScript | Out-File -FilePath $wrapperPath -Encoding ascii
Write-Host "[OK] Wrapper script: $wrapperPath" -ForegroundColor Green

# 3. Remover tarea anterior si existe
$existingTask = Get-ScheduledTask -TaskName $TASK_NAME -ErrorAction SilentlyContinue
if ($existingTask) {
    Unregister-ScheduledTask -TaskName $TASK_NAME -Confirm:$false
    Write-Host "[OK] Tarea anterior removida" -ForegroundColor Yellow
}

# 4. Crear tarea programada
Write-Host "[...] Creando tarea programada..." -ForegroundColor Yellow

$action = New-ScheduledTaskAction -Execute $wrapperPath
$trigger = New-ScheduledTaskTrigger -AtStartup
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)

Register-ScheduledTask -TaskName $TASK_NAME -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description "Ollama LLM Server with CORS enabled for FI Edge"

Write-Host "[OK] Tarea '$TASK_NAME' creada" -ForegroundColor Green

# 5. Iniciar ahora
Write-Host "[...] Iniciando Ollama..." -ForegroundColor Yellow

# Matar instancia existente si hay
Get-Process -Name "ollama*" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

Start-ScheduledTask -TaskName $TASK_NAME
Start-Sleep -Seconds 5

# 6. Verificar
try {
    $response = Invoke-RestMethod -Uri "http://localhost:11434/api/tags" -TimeoutSec 10
    Write-Host "[OK] Ollama corriendo!" -ForegroundColor Green
    Write-Host "     Modelos: $($response.models.name -join ', ')" -ForegroundColor Gray
} catch {
    Write-Host "[WARN] Ollama iniciando... puede tardar unos segundos" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host " Ollama Auto-Start Configurado" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Ollama iniciará automáticamente al reiniciar." -ForegroundColor Green
Write-Host "CORS habilitado: OLLAMA_ORIGINS=*" -ForegroundColor Gray
Write-Host "Escuchando en: 0.0.0.0:11434" -ForegroundColor Gray
Write-Host ""
Write-Host "Comandos útiles:" -ForegroundColor Yellow
Write-Host "  Start-ScheduledTask OllamaServe      # Iniciar" -ForegroundColor Gray
Write-Host "  Stop-ScheduledTask OllamaServe       # Detener" -ForegroundColor Gray
Write-Host "  Get-ScheduledTask OllamaServe        # Ver estado" -ForegroundColor Gray
