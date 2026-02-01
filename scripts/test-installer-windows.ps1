# =============================================================================
# Aurity Desktop v1.0.8 - Installer Validation Script
# =============================================================================
# Purpose: Validate installer on clean Windows machines (NOT Azure VMs)
# Requirements: Windows 10/11, PowerShell 5.1+, Internet connection
# Usage: .\test-installer-windows.ps1 -InstallerPath "C:\path\to\Aurity_1.0.8_x64-setup.exe"
# =============================================================================

param(
    [Parameter(Mandatory=$false)]
    [string]$InstallerPath,

    [Parameter(Mandatory=$false)]
    [switch]$SkipOllama,

    [Parameter(Mandatory=$false)]
    [switch]$Verbose
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue" # Faster downloads

# =============================================================================
# Configuration
# =============================================================================

$AURITY_VERSION = "1.0.8"
$EXPECTED_INSTALL_PATH = "$env:LOCALAPPDATA\Programs\Aurity\Aurity.exe"
$BACKEND_SIDECAR_PATH = "$env:LOCALAPPDATA\Programs\Aurity\binaries\aurity-backend-x86_64-pc-windows-msvc.exe"
$FI_MONITOR_NAME = "FI Monitor"
$OLLAMA_ENDPOINT = "http://localhost:11434"
$BACKEND_PORT = 7001

# Log file
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$logFile = "$env:USERPROFILE\Desktop\aurity-installer-test-$timestamp.log"
$screenshotDir = "$env:USERPROFILE\Desktop\aurity-screenshots-$timestamp"

# Create screenshot directory
New-Item -ItemType Directory -Force -Path $screenshotDir | Out-Null

# =============================================================================
# Helper Functions
# =============================================================================

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")

    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $color = switch ($Level) {
        "ERROR"   { "Red" }
        "WARNING" { "Yellow" }
        "SUCCESS" { "Green" }
        default   { "White" }
    }

    $logEntry = "[$timestamp] [$Level] $Message"
    Write-Host $logEntry -ForegroundColor $color
    Add-Content -Path $logFile -Value $logEntry
}

function Test-AdminPrivileges {
    $currentPrincipal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
    return $currentPrincipal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

function Get-SystemInfo {
    Write-Log "=== SYSTEM INFORMATION ===" "INFO"

    $os = Get-CimInstance Win32_OperatingSystem
    $cpu = Get-CimInstance Win32_Processor
    $ram = [math]::Round($os.TotalVisibleMemorySize / 1MB, 2)

    Write-Log "OS: $($os.Caption) $($os.Version)" "INFO"
    Write-Log "CPU: $($cpu.Name)" "INFO"
    Write-Log "RAM: $ram GB" "INFO"
    Write-Log "PowerShell: $($PSVersionTable.PSVersion)" "INFO"

    # Check GPU (for Ollama)
    try {
        $gpu = Get-CimInstance Win32_VideoController | Select-Object -First 1
        Write-Log "GPU: $($gpu.Name)" "INFO"
    } catch {
        Write-Log "GPU: Not detected (CPU-only mode)" "WARNING"
    }

    # Check if running as admin
    if (Test-AdminPrivileges) {
        Write-Log "Admin: Yes (installer puede no funcionar como admin)" "WARNING"
    } else {
        Write-Log "Admin: No (correcto para instalación normal)" "SUCCESS"
    }
}

function Download-LatestInstaller {
    Write-Log "Descargando installer desde GitHub..." "INFO"

    try {
        # Check if gh CLI installed
        $ghVersion = gh --version 2>$null
        if (-not $ghVersion) {
            Write-Log "GitHub CLI no instalado. Instalando..." "WARNING"
            winget install --id GitHub.cli --silent --accept-source-agreements
        }

        # Download latest release
        $downloadPath = "$env:USERPROFILE\Downloads\Aurity_${AURITY_VERSION}_x64-setup.exe"

        Write-Log "Descargando a: $downloadPath" "INFO"
        gh release download "v$AURITY_VERSION" `
            --repo BernardUriza/free-intelligence `
            --pattern "Aurity_*_x64-setup.exe" `
            --output $downloadPath `
            --clobber

        if (Test-Path $downloadPath) {
            Write-Log "Installer descargado: $downloadPath" "SUCCESS"
            return $downloadPath
        } else {
            throw "Download failed - file not found"
        }
    } catch {
        Write-Log "Error descargando installer: $_" "ERROR"
        throw
    }
}

function Verify-InstallerHash {
    param([string]$Path)

    Write-Log "Verificando integridad del installer..." "INFO"

    $hash = (Get-FileHash -Path $Path -Algorithm SHA256).Hash.ToLower()
    $size = [math]::Round((Get-Item $Path).Length / 1MB, 2)

    Write-Log "SHA256: $hash" "INFO"
    Write-Log "Size: $size MB" "INFO"

    # TODO: Compare with expected hash from release notes
    # For now, just verify size is reasonable (50-200 MB)
    if ($size -lt 50 -or $size -gt 300) {
        Write-Log "WARNING: Installer size unusual ($size MB)" "WARNING"
    } else {
        Write-Log "Size verification: OK" "SUCCESS"
    }
}

function Install-Aurity {
    param([string]$InstallerPath)

    Write-Log "=== INSTALACIÓN ===" "INFO"
    Write-Log "ACCIÓN MANUAL REQUERIDA:" "WARNING"
    Write-Log "1. El installer se abrirá automáticamente" "WARNING"
    Write-Log "2. Haz screenshots de CADA paso (SmartScreen, wizard, etc.)" "WARNING"
    Write-Log "3. Guarda screenshots en: $screenshotDir" "WARNING"
    Write-Log "4. Regresa aquí cuando termine la instalación" "WARNING"
    Write-Log "" "INFO"

    # Launch installer
    Write-Log "Lanzando installer..." "INFO"
    Start-Process -FilePath $InstallerPath -Wait

    # Wait for user confirmation
    Write-Host "`n=== CHECKLIST DE INSTALACIÓN ===" -ForegroundColor Cyan
    Write-Host "[ ] SmartScreen warning apareció?" -ForegroundColor Yellow
    Write-Host "[ ] Hiciste click en 'More info' → 'Run anyway'?" -ForegroundColor Yellow
    Write-Host "[ ] Installer mostró progress bar?" -ForegroundColor Yellow
    Write-Host "[ ] Install location se mostró?: $env:LOCALAPPDATA\Programs\Aurity" -ForegroundColor Yellow
    Write-Host "[ ] Desktop shortcut creado?" -ForegroundColor Yellow
    Write-Host "[ ] Start menu entry creado?" -ForegroundColor Yellow
    Write-Host "`n¿Instalación completa? Presiona ENTER para continuar..." -ForegroundColor Green
    Read-Host

    Write-Log "Continuando con verificación..." "INFO"
}

function Verify-Installation {
    Write-Log "=== VERIFICACIÓN DE INSTALACIÓN ===" "INFO"

    # Check app exists
    if (Test-Path $EXPECTED_INSTALL_PATH) {
        $version = (Get-Item $EXPECTED_INSTALL_PATH).VersionInfo.FileVersion
        Write-Log "✅ App instalada: $EXPECTED_INSTALL_PATH" "SUCCESS"
        Write-Log "   Version: $version" "INFO"
    } else {
        Write-Log "❌ App NO encontrada en path esperado" "ERROR"
        throw "Installation failed - app not found"
    }

    # Check backend sidecar
    if (Test-Path $BACKEND_SIDECAR_PATH) {
        Write-Log "✅ Backend sidecar encontrado" "SUCCESS"
    } else {
        Write-Log "⚠️ Backend sidecar NO encontrado (puede estar en otro path)" "WARNING"
    }

    # Check shortcuts
    $desktopShortcut = "$env:USERPROFILE\Desktop\Aurity.lnk"
    $startMenuShortcut = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Aurity.lnk"

    if (Test-Path $desktopShortcut) {
        Write-Log "✅ Desktop shortcut creado" "SUCCESS"
    } else {
        Write-Log "⚠️ Desktop shortcut NO encontrado" "WARNING"
    }

    if (Test-Path $startMenuShortcut) {
        Write-Log "✅ Start menu entry creado" "SUCCESS"
    } else {
        Write-Log "⚠️ Start menu entry NO encontrado" "WARNING"
    }
}

function Test-AppLaunch {
    Write-Log "=== LANZAMIENTO DE APP ===" "INFO"

    Write-Log "Lanzando Aurity..." "INFO"
    Start-Process -FilePath $EXPECTED_INSTALL_PATH

    Write-Log "Esperando 10 segundos para startup..." "INFO"
    Start-Sleep -Seconds 10

    # Verify process running
    $proc = Get-Process -Name "Aurity" -ErrorAction SilentlyContinue
    if ($proc) {
        $memory = [math]::Round($proc.WorkingSet64 / 1MB, 2)
        Write-Log "✅ App corriendo (PID: $($proc.Id))" "SUCCESS"
        Write-Log "   Memory: $memory MB" "INFO"
    } else {
        Write-Log "❌ App NO está corriendo" "ERROR"
        throw "App launch failed"
    }

    # Check backend sidecar process
    Start-Sleep -Seconds 5
    $backendProc = Get-Process | Where-Object { $_.ProcessName -like "*aurity-backend*" }
    if ($backendProc) {
        Write-Log "✅ Backend sidecar corriendo (PID: $($backendProc.Id))" "SUCCESS"
    } else {
        Write-Log "⚠️ Backend sidecar NO detectado (puede estar usando Python sidecar)" "WARNING"
    }

    # Check backend port
    $portCheck = Get-NetTCPConnection -LocalPort $BACKEND_PORT -ErrorAction SilentlyContinue
    if ($portCheck) {
        Write-Log "✅ Backend listening en puerto $BACKEND_PORT" "SUCCESS"
    } else {
        # Try ports 7002-7010
        $found = $false
        for ($port = 7002; $port -le 7010; $port++) {
            $altPort = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
            if ($altPort) {
                Write-Log "⚠️ Backend en puerto alternativo: $port" "WARNING"
                $found = $true
                break
            }
        }
        if (-not $found) {
            Write-Log "⚠️ Backend NO detectado en puertos 7001-7010" "WARNING"
        }
    }
}

function Test-OllamaIntegration {
    if ($SkipOllama) {
        Write-Log "=== OLLAMA INTEGRATION (SKIPPED) ===" "INFO"
        return
    }

    Write-Log "=== OLLAMA INTEGRATION ===" "INFO"

    # Check if Ollama installed
    $ollamaInstalled = Get-Command ollama -ErrorAction SilentlyContinue
    if (-not $ollamaInstalled) {
        Write-Log "Ollama NO instalado. ¿Instalar ahora? (y/n)" "WARNING"
        $install = Read-Host
        if ($install -eq 'y') {
            Write-Log "Instalando Ollama..." "INFO"
            winget install --id Ollama.Ollama --silent
            Write-Log "Ollama instalado. Reinicia PowerShell y re-corre este script." "SUCCESS"
            exit
        } else {
            Write-Log "Saltando tests de Ollama" "WARNING"
            return
        }
    }

    Write-Log "Ollama instalado: $(ollama --version)" "SUCCESS"

    # Check if Ollama running
    try {
        $response = Invoke-RestMethod -Uri "$OLLAMA_ENDPOINT/api/tags" -Method GET -TimeoutSec 5
        Write-Log "✅ Ollama corriendo en $OLLAMA_ENDPOINT" "SUCCESS"

        # List models
        $models = $response.models
        if ($models.Count -gt 0) {
            Write-Log "Modelos instalados:" "INFO"
            foreach ($model in $models) {
                Write-Log "  - $($model.name)" "INFO"
            }
        } else {
            Write-Log "⚠️ No hay modelos instalados. Pull llama3.1:8b?" "WARNING"
            $pull = Read-Host "(y/n)"
            if ($pull -eq 'y') {
                Write-Log "Pulling llama3.1:8b (esto tomará varios minutos)..." "INFO"
                ollama pull llama3.1:8b
                Write-Log "Modelo descargado" "SUCCESS"
            }
        }
    } catch {
        Write-Log "❌ Ollama NO está corriendo" "ERROR"
        Write-Log "Inicia Ollama y re-corre este script" "WARNING"
        return
    }

    # Test Ollama detection in Aurity
    Write-Log "`n=== VERIFICACIÓN MANUAL: Ollama en Aurity ===" "WARNING"
    Write-Log "1. Ve a Aurity (debe estar corriendo)" "WARNING"
    Write-Log "2. ¿Ves 'IA Local: Conectada' o similar?" "WARNING"
    Write-Log "3. ¿Puedes crear sesión con LLM features?" "WARNING"
    Write-Host "`n¿Ollama detectado correctamente en Aurity? (y/n): " -ForegroundColor Yellow -NoNewline
    $detected = Read-Host

    if ($detected -eq 'y') {
        Write-Log "✅ Ollama integration funciona" "SUCCESS"
    } else {
        Write-Log "❌ Ollama NO detectado en Aurity (bug potencial)" "ERROR"
    }
}

function Test-FIMonitorIntegration {
    Write-Log "=== FI MONITOR INTEGRATION ===" "INFO"

    # Check if FI Monitor installed
    $fiMonitor = Get-Process | Where-Object { $_.ProcessName -like "*fi-monitor*" -or $_.MainWindowTitle -like "*FI Monitor*" }

    if ($fiMonitor) {
        Write-Log "✅ FI Monitor corriendo (PID: $($fiMonitor.Id))" "SUCCESS"
    } else {
        Write-Log "⚠️ FI Monitor NO detectado" "WARNING"
        Write-Log "Verifica que DesktopSetupWizard lo instaló correctamente" "WARNING"
    }

    # Manual verification
    Write-Log "`n=== VERIFICACIÓN MANUAL: FI Monitor ===" "WARNING"
    Write-Log "1. ¿DesktopSetupWizard apareció al abrir Aurity?" "WARNING"
    Write-Log "2. ¿Instaló FI Monitor automáticamente?" "WARNING"
    Write-Log "3. ¿FI Monitor mostró su propio wizard (Python + Ollama)?" "WARNING"
    Write-Host "`n¿FI Monitor funciona correctamente? (y/n): " -ForegroundColor Yellow -NoNewline
    $works = Read-Host

    if ($works -eq 'y') {
        Write-Log "✅ FI Monitor integration OK" "SUCCESS"
    } else {
        Write-Log "❌ FI Monitor tiene issues (documentar)" "ERROR"
    }
}

function Run-E2EUserJourney {
    Write-Log "=== E2E USER JOURNEY ===" "INFO"

    Write-Host "`n=== FLUJO COMPLETO A PROBAR ===" -ForegroundColor Cyan
    Write-Host "1. First-run wizard (DesktopSetupWizard)" -ForegroundColor White
    Write-Host "2. Login con Auth0 (browser redirect)" -ForegroundColor White
    Write-Host "3. Dashboard carga correctamente" -ForegroundColor White
    Write-Host "4. Crear nueva sesión" -ForegroundColor White
    Write-Host "5. Generar SOAP note (si Ollama disponible)" -ForegroundColor White
    Write-Host "6. Guardar y cerrar sesión" -ForegroundColor White
    Write-Host "7. Logout y re-login" -ForegroundColor White

    Write-Host "`n=== INSTRUCCIONES ===" -ForegroundColor Yellow
    Write-Host "Ejecuta cada paso manualmente y reporta resultados." -ForegroundColor Yellow
    Write-Host "Toma screenshots de CADA paso." -ForegroundColor Yellow
    Write-Host "Guarda screenshots en: $screenshotDir" -ForegroundColor Yellow

    Write-Host "`nPresiona ENTER cuando hayas terminado el E2E journey..." -ForegroundColor Green
    Read-Host

    # Bug report template
    Write-Host "`n=== REPORTE DE BUGS ===" -ForegroundColor Cyan
    Write-Host "¿Encontraste bugs? (y/n): " -ForegroundColor Yellow -NoNewline
    $hasBugs = Read-Host

    if ($hasBugs -eq 'y') {
        $bugReport = "$env:USERPROFILE\Desktop\aurity-bugs-$timestamp.md"

        $template = @"
# Aurity Desktop v$AURITY_VERSION - Bug Report
**Date:** $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
**Machine:** $env:COMPUTERNAME
**Windows:** $((Get-CimInstance Win32_OperatingSystem).Caption)

## Bugs Encontrados

### Bug #1: [TÍTULO]
**Severity:** P0 / P1 / P2 / P3
**Steps to Reproduce:**
1.
2.
3.

**Expected:**
**Actual:**
**Screenshot:** [Ver $screenshotDir]
**Workaround:** [Si existe]

---

### Bug #2: [TÍTULO]
...

## Summary
- Total bugs: [X]
- P0 (blocker): [X]
- P1 (high): [X]
- P2 (medium): [X]
- P3 (low): [X]

## Recommendations
[¿Ship as-is o fix first?]
"@

        Set-Content -Path $bugReport -Value $template
        Write-Log "Template de bug report creado: $bugReport" "SUCCESS"
        Write-Log "Edita el archivo y documenta bugs encontrados" "INFO"

        # Open bug report in notepad
        Start-Process notepad.exe $bugReport
    } else {
        Write-Log "✅ No se encontraron bugs críticos" "SUCCESS"
    }
}

function Generate-TestReport {
    Write-Log "=== GENERANDO REPORTE FINAL ===" "INFO"

    $reportPath = "$env:USERPROFILE\Desktop\aurity-test-report-$timestamp.md"

    $report = @"
# Aurity Desktop v$AURITY_VERSION - Installer Test Report

**Date:** $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
**Machine:** $env:COMPUTERNAME
**OS:** $((Get-CimInstance Win32_OperatingSystem).Caption)
**Tester:** $env:USERNAME

---

## Test Summary

### Installation
- [ ] Installer descargado correctamente
- [ ] Hash verification passed
- [ ] SmartScreen bypass claro (2 clicks)
- [ ] Install completa sin errores
- [ ] App lanza en first run

### Ollama Integration
- [ ] Ollama instalado
- [ ] Ollama detectado cuando running
- [ ] Fallback graceful cuando offline
- [ ] Dynamic detection después de startup

### FI Monitor Integration
- [ ] DesktopSetupWizard apareció
- [ ] FI Monitor instalado automáticamente
- [ ] FI Monitor wizard funciona (Python + Ollama)

### Core Features
- [ ] Auth0 login works
- [ ] Dashboard carga
- [ ] Puede crear sesión
- [ ] SOAP generation funciona (con Ollama)

---

## Screenshots
Ver directorio: $screenshotDir

## Full Log
Ver archivo: $logFile

## Bugs Found
[Link al bug report si existe]

## Recommendation
- [ ] ✅ SHIP - Ready para usuarios
- [ ] ⚠️ FIX MINOR - Ship con bugs conocidos + documentación
- [ ] ❌ BLOCKER - Fix P0 bugs antes de invitar usuarios

---

**Generated by:** test-installer-windows.ps1
"@

    Set-Content -Path $reportPath -Value $report
    Write-Log "Reporte generado: $reportPath" "SUCCESS"

    # Open report
    Start-Process notepad.exe $reportPath
}

# =============================================================================
# Main Script
# =============================================================================

function Main {
    Write-Host @"
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║   AURITY DESKTOP v$AURITY_VERSION - INSTALLER VALIDATION SCRIPT   ║
║                                                                   ║
║   Purpose: Validate installer on clean Windows machines          ║
║   Author: Free Intelligence Team                                 ║
║   Date: $(Get-Date -Format "yyyy-MM-dd")                         ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
"@ -ForegroundColor Cyan

    Write-Log "Iniciando test de installer..." "INFO"
    Write-Log "Log file: $logFile" "INFO"
    Write-Log "Screenshot dir: $screenshotDir" "INFO"
    Write-Log "" "INFO"

    # Step 1: System info
    Get-SystemInfo
    Write-Log "" "INFO"

    # Step 2: Download installer if not provided
    if (-not $InstallerPath) {
        $InstallerPath = Download-LatestInstaller
    } elseif (-not (Test-Path $InstallerPath)) {
        Write-Log "Installer path inválido: $InstallerPath" "ERROR"
        throw "Installer not found"
    }
    Write-Log "" "INFO"

    # Step 3: Verify hash
    Verify-InstallerHash -Path $InstallerPath
    Write-Log "" "INFO"

    # Step 4: Install
    Install-Aurity -InstallerPath $InstallerPath
    Write-Log "" "INFO"

    # Step 5: Verify installation
    Verify-Installation
    Write-Log "" "INFO"

    # Step 6: Test app launch
    Test-AppLaunch
    Write-Log "" "INFO"

    # Step 7: Test Ollama
    Test-OllamaIntegration
    Write-Log "" "INFO"

    # Step 8: Test FI Monitor
    Test-FIMonitorIntegration
    Write-Log "" "INFO"

    # Step 9: E2E user journey
    Run-E2EUserJourney
    Write-Log "" "INFO"

    # Step 10: Generate report
    Generate-TestReport

    Write-Log "=== TEST COMPLETO ===" "SUCCESS"
    Write-Log "Ver reporte en Desktop" "INFO"
    Write-Log "Screenshots guardados en: $screenshotDir" "INFO"
}

# Run main
try {
    Main
} catch {
    Write-Log "FATAL ERROR: $_" "ERROR"
    Write-Log "Stack trace: $($_.ScriptStackTrace)" "ERROR"
    exit 1
}
