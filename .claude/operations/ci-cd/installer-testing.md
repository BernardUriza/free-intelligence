# Installer Testing Strategy (Azure VMs)

**Context:** Antes de liberar a pilotos reales, validar el instalador en VMs limpias de Azure para detectar issues de compatibilidad, instalación, y UX.

**Last Updated:** 2026-01-20

---

## Azure VM Setup

### 1. Crear VMs de Testing

```bash
# Windows 10 (x86_64)
az vm create \
  --resource-group aurity-testing \
  --name aurity-win10-test \
  --image Win10-22H2-Pro \
  --size Standard_D2s_v3 \
  --admin-username azureuser \
  --admin-password '<STRONG_PASSWORD>' \
  --location eastus \
  --public-ip-sku Standard

# Windows 11 (x86_64)
az vm create \
  --resource-group aurity-testing \
  --name aurity-win11-test \
  --image Win11-23H2-Pro \
  --size Standard_D2s_v3 \
  --admin-username azureuser \
  --admin-password '<STRONG_PASSWORD>' \
  --location eastus \
  --public-ip-sku Standard

# Windows Server 2022 (para validar enterprise environments)
az vm create \
  --resource-group aurity-testing \
  --name aurity-server2022-test \
  --image WindowsServer:WindowsServer:2022-datacenter-azure-edition:latest \
  --size Standard_D2s_v3 \
  --admin-username azureuser \
  --admin-password '<STRONG_PASSWORD>' \
  --location eastus \
  --public-ip-sku Standard
```

### 2. Obtener IPs para Conexión

```bash
# Listar todas las VMs
az vm list --output table

# Obtener IP pública de una VM específica
az vm list-ip-addresses \
  --name aurity-win10-test \
  --resource-group aurity-testing \
  --output table
```

### 3. Conectar via RDP (macOS)

```bash
# Opción A: GUI (Microsoft Remote Desktop app)
open rdp://<VM_PUBLIC_IP>

# Opción B: Script de conexión automatizada
cat > connect-vm.sh <<'EOF'
#!/bin/bash
VM_NAME=$1
IP=$(az vm list-ip-addresses --name $VM_NAME --resource-group aurity-testing --query "[0].virtualMachine.network.publicIpAddresses[0].ipAddress" -o tsv)
echo "Conectando a $VM_NAME ($IP)..."
open "rdp://full%20address=s:$IP"
EOF
chmod +x connect-vm.sh

# Uso:
./connect-vm.sh aurity-win10-test
```

---

## Testing Checklist (Ejecutar en CADA VM)

### Pre-Testing Setup

```powershell
# Dentro de la VM (PowerShell)

# 1. Instalar GitHub CLI (para descargar releases privados)
winget install --id GitHub.cli

# 2. Autenticar con GitHub
gh auth login

# 3. Crear directorio de testing
New-Item -Path "$env:USERPROFILE\AurityTest" -ItemType Directory
cd "$env:USERPROFILE\AurityTest"
```

### Test Script (Copiar y Ejecutar en VM)

```powershell
# test-aurity-install.ps1
$ErrorActionPreference = "Stop"
$logFile = "$env:USERPROFILE\AurityTest\install-test-$(Get-Date -Format 'yyyyMMdd-HHmmss').log"

function Log($message) {
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$timestamp - $message" | Tee-Object -FilePath $logFile -Append
}

Log "=== Aurity Desktop Install Test ==="
Log "VM: $env:COMPUTERNAME"
Log "Windows: $((Get-CimInstance Win32_OperatingSystem).Caption)"
Log "Version: $((Get-CimInstance Win32_OperatingSystem).Version)"

# 1. Descargar instalador
Log "Descargando instalador..."
gh release download v1.0.1 --repo BernardUriza/free-intelligence --pattern "*.exe" --clobber

# 2. Verificar hash SHA256
Log "Verificando integridad..."
$expectedHash = "ca72b835150e664f4155504612f3d1ec6f2731f9d99251f183d1bea2dbec0336"
$actualHash = (Get-FileHash "Aurity_1.0.0_x64-setup.exe" -Algorithm SHA256).Hash.ToLower()
if ($actualHash -ne $expectedHash) {
    Log "❌ HASH MISMATCH - ABORTANDO"
    Log "Expected: $expectedHash"
    Log "Actual:   $actualHash"
    exit 1
}
Log "✅ Hash verificado"

# 3. Instalar (modo interactivo para documentar SmartScreen)
Log "=== ACCIÓN MANUAL REQUERIDA ==="
Log "1. SmartScreen warning aparece?"
Log "2. Click 'More info'"
Log "3. Click 'Run anyway'"
Log "4. Esperar instalación (tomar screenshot de cada paso)"
Read-Host "Presiona ENTER cuando instalación termine"

# 4. Verificar instalación
$appPath = "$env:LOCALAPPDATA\Programs\Aurity\Aurity.exe"
if (Test-Path $appPath) {
    Log "✅ App instalada: $appPath"
    $version = (Get-Item $appPath).VersionInfo.FileVersion
    Log "Version reportada: $version"
} else {
    Log "❌ App NO encontrada en ubicación esperada"
    exit 1
}

# 5. Lanzar app
Log "Lanzando app..."
Start-Process $appPath

# 6. Esperar y verificar proceso
Start-Sleep -Seconds 10
$proc = Get-Process -Name "Aurity" -ErrorAction SilentlyContinue
if ($proc) {
    Log "✅ App corriendo (PID: $($proc.Id))"
    Log "Memory: $([math]::Round($proc.WorkingSet64/1MB, 2)) MB"
} else {
    Log "❌ App NO está corriendo"

    # Buscar logs de crash
    $logPath = "$env:APPDATA\com.aurity.desktop\logs"
    if (Test-Path $logPath) {
        Log "=== Logs de App ==="
        Get-ChildItem $logPath -Filter "*.log" | ForEach-Object {
            Log "--- $($_.Name) ---"
            Get-Content $_.FullName -Tail 20 | ForEach-Object { Log $_ }
        }
    }
    exit 1
}

# 7. Verificar backend sidecar
Start-Sleep -Seconds 5
$backendPort = netstat -ano | Select-String ":7001.*LISTENING"
if ($backendPort) {
    Log "✅ Backend sidecar corriendo (puerto 7001)"
} else {
    Log "⚠️ Backend sidecar NO detectado en puerto 7001"
}

# 8. Testing manual checkpoint
Log ""
Log "=== TESTING MANUAL REQUERIDO (Documentar con screenshots) ==="
Log "1. ✅/❌ Auth0 login funciona?"
Log "2. ✅/❌ Dashboard carga correctamente?"
Log "3. ✅/❌ Navegación entre secciones funciona?"
Log "4. ✅/❌ App maneja gracefully la ausencia de Ollama?"
Log "5. ✅/❌ Menú y UI responsive?"
Log ""
Log "Resultado guardado en: $logFile"
```

### Manual Testing Checklist

Después de ejecutar el script, validar manualmente:

| Test | Esperado | ✅/❌ | Notas |
|------|----------|-------|-------|
| **Instalación** |
| SmartScreen warning aparece | Sí (2 clicks: "More info" → "Run anyway") | | |
| Instalación sin permisos admin | User puede instalar en $LOCALAPPDATA | | |
| Shortcut en Start Menu | "Aurity" aparece en Start | | |
| Shortcut en Desktop | Opcional (checkbox en instalador?) | | |
| Tiempo de instalación | <2 minutos | | |
| **Primera Ejecución** |
| App lanza sin errores | Ventana principal abre | | |
| Auth0 login redirect | Redirect a auth.aurity.io funciona | | |
| Login exitoso | Redirect back a app funciona | | |
| Dashboard carga | UI completa sin errores | | |
| **Backend Sidecar** |
| FastAPI inicia | Puerto 7001 en LISTEN | | |
| Health check | `curl localhost:7001/api/health` responde | | |
| **Ollama Detection** |
| Sin Ollama instalado | App NO crashea (degraded mode) | | |
| Error message claro | "Ollama not detected" visible | | |
| **Performance** |
| Tiempo de inicio | <10 segundos | | |
| Uso de memoria | <500 MB en idle | | |
| CPU usage | <5% en idle | | |
| **Auto-Updater (si v1.0.2+ existe)** |
| Detecta update | Notificación visible | | |
| Download funciona | Progress bar visible | | |
| Install funciona | App reinicia con nueva version | | |

---

## Post-Testing

### 1. Documentar Issues

Si encuentras bugs, crea GitHub issues inmediatamente:

```bash
# En tu Mac (no en la VM)
gh issue create \
  --title "[Windows 10] SmartScreen bypass confuso" \
  --body "**VM:** aurity-win10-test
**Síntoma:** Users no encuentran botón 'More info'
**Screenshots:** (adjuntar)
**Propuesta:** Agregar instrucciones visuales en release notes" \
  --label "bug,windows,installer"
```

### 2. Limpiar VMs (ahorrar costos)

```bash
# Detener VM (mantiene disco, no cobra compute)
az vm deallocate --name aurity-win10-test --resource-group aurity-testing

# Eliminar VM completamente
az vm delete --name aurity-win10-test --resource-group aurity-testing --yes

# Eliminar resource group completo (todas las VMs)
az group delete --name aurity-testing --yes
```

### 3. Actualizar Documentación

Después de testing, actualizar este archivo con:
- Issues encontrados
- Workarounds aplicados
- Mejoras al proceso de testing

---

## Testing Matrix (Plataformas)

| Windows Version | VM Size | Status | Issues Found | Tested By | Date |
|-----------------|---------|--------|--------------|-----------|------|
| Windows 10 22H2 | Standard_D2s_v3 | ⏳ Pending | - | - | - |
| Windows 11 23H2 | Standard_D2s_v3 | ⏳ Pending | - | - | - |
| Server 2022 | Standard_D2s_v3 | ⏳ Pending | - | - | - |

---

## Cost Estimation

| VM Size | Cost per Hour | Daily Cost (24h) | Testing Cost (2h) |
|---------|---------------|------------------|-------------------|
| Standard_D2s_v3 | ~$0.096/hr | ~$2.30/day | ~$0.20 |

**Tip:** Deallocate VMs cuando no las uses para evitar cargos de compute (solo pagas storage).

---

## Troubleshooting

### Issue: No puedo conectar via RDP

**Causa:** NSG (Network Security Group) bloqueando puerto 3389

**Fix:**
```bash
az vm open-port --port 3389 --resource-group aurity-testing --name aurity-win10-test
```

### Issue: gh CLI no puede descargar release (repo privado)

**Causa:** Token de autenticación no tiene permisos

**Fix:**
```powershell
# En la VM, re-autenticar con scope correcto
gh auth login --scopes repo
```

### Issue: Hash SHA256 no coincide

**Causa:** Download corrupto o archivo incorrecto

**Fix:**
```powershell
# Re-descargar
Remove-Item "Aurity_*.exe"
gh release download v1.0.1 --repo BernardUriza/free-intelligence --pattern "*.exe" --clobber
```

---

## Future Improvements

- [ ] Automatizar testing con Playwright + Windows runners
- [ ] Matrix de testing con GitHub Actions (Win10/11/Server)
- [ ] Screenshots automáticos de cada paso del instalador
- [ ] Video recording de instalación completa
- [ ] Smoke tests automáticos post-install (Selenium)

---

**Ver también:**
- `.claude/rules/ci-cd/windows-builds.md` - Debugging journey (16 errores resueltos)
- `.claude/rules/architecture/desktop-app.md` - Arquitectura de Tauri app
