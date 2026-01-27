# VM Testing Commands for Bernard
# Ejecutar estos comandos DENTRO de la VM Win11

# ======================
# STEP 1: Setup (Solo primera vez)
# ======================

# Instalar GitHub CLI
winget install --id GitHub.cli

# IMPORTANTE: Cerrar y re-abrir PowerShell después de instalar gh CLI

# Autenticar con GitHub
gh auth login
# Elegir:
#   - GitHub.com
#   - HTTPS
#   - Yes (login with web browser)
#   - Copiar código y pegar en browser

# Verificar autenticación
gh auth status

# Crear directorio testing
New-Item -Path "$env:USERPROFILE\AurityTest" -ItemType Directory -Force
cd "$env:USERPROFILE\AurityTest"

# ======================
# STEP 2: Descargar instalador (cuando build complete)
# ======================

# Descargar nuevo instalador con WebView2
gh run download 21192021808 --name aurity-windows-nsis --dir "$env:USERPROFILE\AurityTest" --repo BernardUriza/free-intelligence

# Verificar archivo descargado
$exe = Get-ChildItem "$env:USERPROFILE\AurityTest\Aurity*.exe" | Select-Object -First 1
Write-Host "📦 Archivo: $($exe.Name)"
Write-Host "📏 Tamaño: $([math]::Round($exe.Length/1MB, 2)) MB"
Write-Host "🔐 SHA256: $((Get-FileHash $exe.FullName -Algorithm SHA256).Hash.ToLower())"

# ======================
# STEP 3: Verificar WebView2 ANTES de instalar
# ======================

Write-Host "`n=== WebView2 Status BEFORE Install ==="
$webview2Before = Get-ItemProperty "HKLM:\SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}" -ErrorAction SilentlyContinue
if ($webview2Before) {
    Write-Host "✅ WebView2 ya instalado (Version: $($webview2Before.pv))"
} else {
    Write-Host "⚠️ WebView2 NO instalado (bootstrapper debería instalarlo durante setup)"
}

# ======================
# STEP 4: Instalar Aurity (MANUAL)
# ======================

Write-Host "`n=== INSTALACIÓN MANUAL ==="
Write-Host "1. Doble-click en: $($exe.FullName)"
Write-Host "2. SmartScreen: Click 'More info' → 'Run anyway'"
Write-Host "3. OBSERVAR: ¿Aparece progreso 'Installing WebView2'?"
Write-Host "4. Esperar instalación completa"

# Abrir explorador en la carpeta del exe
explorer.exe "/select,$($exe.FullName)"

Write-Host "`nPresiona ENTER cuando instalación termine..."
Read-Host

# ======================
# STEP 5: Verificar WebView2 DESPUÉS de instalar
# ======================

Write-Host "`n=== WebView2 Status AFTER Install ==="
$webview2After = Get-ItemProperty "HKLM:\SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}" -ErrorAction SilentlyContinue
if ($webview2After) {
    Write-Host "✅ WebView2 instalado (Version: $($webview2After.pv))"
    if ($webview2Before -eq $null) {
        Write-Host "🎉 WebView2 fue instalado por el bootstrapper! (SUCCESS)"
    }
} else {
    Write-Host "❌ WebView2 SIGUE sin instalar - BOOTSTRAPPER FALLÓ"
}

# ======================
# STEP 6: Verificar app instalada
# ======================

Write-Host "`n=== App Verification ==="
$appPath = "$env:LOCALAPPDATA\Programs\Aurity\Aurity.exe"
if (Test-Path $appPath) {
    Write-Host "✅ App instalada: $appPath"
    $appVersion = (Get-Item $appPath).VersionInfo.FileVersion
    Write-Host "Version: $appVersion"
} else {
    Write-Host "❌ App NO encontrada en ubicación esperada"
}

# ======================
# STEP 7: Lanzar y verificar
# ======================

Write-Host "`n=== Launching App ==="
if (Test-Path $appPath) {
    Start-Process $appPath
    Write-Host "App lanzada, esperando 10 segundos..."
    Start-Sleep -Seconds 10

    # Verificar proceso
    $proc = Get-Process -Name "Aurity" -ErrorAction SilentlyContinue
    if ($proc) {
        Write-Host "✅ App corriendo (PID: $($proc.Id))"
        Write-Host "RAM: $([math]::Round($proc.WorkingSet64/1MB, 2)) MB"
    } else {
        Write-Host "❌ App NO está corriendo"

        # Buscar logs
        $logPath = "$env:APPDATA\com.aurity.desktop\logs"
        if (Test-Path $logPath) {
            Write-Host "`n=== App Logs ==="
            Get-ChildItem $logPath -Filter "*.log" | ForEach-Object {
                Write-Host "`n--- $($_.Name) ---"
                Get-Content $_.FullName -Tail 20
            }
        }
    }
}

# ======================
# STEP 8: Verificar backend sidecar
# ======================

Write-Host "`n=== Backend Sidecar ==="
Start-Sleep -Seconds 5
$backendPort = netstat -ano | Select-String ":7001.*LISTENING"
if ($backendPort) {
    Write-Host "✅ Backend sidecar corriendo (puerto 7001)"
} else {
    Write-Host "⚠️ Backend sidecar NO detectado en puerto 7001"
}

Write-Host "`n=== Testing Manual Requerido ==="
Write-Host "1. ✅/❌ Auth0 login funciona?"
Write-Host "2. ✅/❌ Dashboard carga correctamente?"
Write-Host "3. ✅/❌ Navegación entre secciones funciona?"
Write-Host "4. ✅/❌ App maneja gracefully la ausencia de Ollama?"

Write-Host "`n🎉 Testing script completo!"
