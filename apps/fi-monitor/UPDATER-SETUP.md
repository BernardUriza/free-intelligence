# FI Monitor Auto-Update Setup

Auto-update está implementado usando `tauri-plugin-updater`. Cuando lances una nueva versión en GitHub Releases, la app se actualizará automáticamente.

## 🔐 Paso 1: Generar Claves de Firma (Una sola vez)

Las claves son necesarias para firmar las actualizaciones y evitar que alguien inyecte malware.

```powershell
# Opción A: Usar el script automático
powershell -ExecutionPolicy Bypass -File C:\temp\gen-keys-auto.ps1

# Opción B: Manual
cd apps/fi-monitor/src-tauri
npx @tauri-apps/cli signer generate -w ~/.tauri/fi-monitor.key
# Presiona ENTER dos veces cuando pida password (dejarlo vacío)
```

Esto generará:
- Clave privada: `~/.tauri/fi-monitor.key` (⚠️ NUNCA commitear esto a git)
- Clave pública: `~/.tauri/fi-monitor.key.pub` (esta sí va en el código)

## 📝 Paso 2: Actualizar tauri.conf.json

Copia el contenido de `~/.tauri/fi-monitor.key.pub` y reemplaza el placeholder en:

```json
"plugins": {
  "updater": {
    "pubkey": "PEGAR_AQUI_LA_CLAVE_PUBLICA",
    ...
  }
}
```

## 🚀 Paso 3: Build y Release

Cuando quieras lanzar una actualización:

```bash
# 1. Incrementar versión en Cargo.toml y tauri.conf.json
# Por ejemplo: 1.0.0 -> 1.0.1

# 2. Build release
cd apps/fi-monitor/src-tauri
cargo build --release

# 3. Crear el instalador firmado
npx @tauri-apps/cli build --ci

# Esto genera:
# - target/release/bundle/nsis/FI Monitor_1.0.1_x64-setup.nsis.zip
# - target/release/bundle/nsis/FI Monitor_1.0.1_x64-setup.nsis.zip.sig (firma)
```

## 📦 Paso 4: Publicar GitHub Release

```bash
# 1. Tag la versión
git tag v1.0.1
git push origin v1.0.1

# 2. Crear GitHub Release con estos archivos:
# - FI Monitor_1.0.1_x64-setup.nsis.zip
# - FI Monitor_1.0.1_x64-setup.nsis.zip.sig

# 3. Crear fi-monitor-updater.json con este contenido:
{
  "version": "1.0.1",
  "notes": "Fix: cloudflared ahora corre headless sin ventanas",
  "pub_date": "2026-01-14T02:00:00Z",
  "platforms": {
    "windows-x86_64": {
      "signature": "<CONTENIDO_DEL_ARCHIVO_.sig>",
      "url": "https://github.com/BernardUriza/free-intelligence/releases/download/v1.0.1/FI Monitor_1.0.1_x64-setup.nsis.zip"
    }
  }
}
```

## ⚡ Cómo Funciona

1. **Al iniciar FI-monitor:**
   - Verifica en `https://github.com/.../fi-monitor-updater.json`
   - Compara versión actual vs disponible
   - Si hay update: descarga, verifica firma, instala

2. **Instalación:**
   - Windows: Instalador NSIS con modo `passive` (sin UI)
   - Usuario solo ve notificación "Update instalado, reinicia la app"

3. **Seguridad:**
   - Firma digital verifica que el update es legítimo
   - Si la firma no coincide, rechaza el update

## 🔒 Seguridad de las Claves

⚠️ **CRÍTICO:**
- La clave privada (`~/.tauri/fi-monitor.key`) NUNCA debe estar en git
- Agrégala a `.gitignore` si no está ya
- Guárdala en un password manager (1Password, Bitwarden, etc.)
- Solo Bernard debe tener acceso a esta clave

Si la clave se pierde:
- Generar nueva clave
- Actualizar pubkey en tauri.conf.json
- Lanzar nueva versión "manual" para todos los usuarios
- Después los updates funcionarán normalmente

## 🧪 Testing

Para probar auto-update localmente:

```bash
# 1. Build versión 1.0.0
# 2. Instalar
# 3. Incrementar a 1.0.1
# 4. Build y crear release local
# 5. Modificar endpoint en tauri.conf.json a tu servidor local
# 6. Lanzar 1.0.0 y verificar que descargue 1.0.1
```

## 📚 Referencias

- [Tauri Updater Docs](https://v2.tauri.app/plugin/updater/)
- [Signer CLI](https://v2.tauri.app/reference/cli/#signer)
- [GitHub Releases Guide](https://docs.github.com/en/repositories/releasing-projects-on-github)
