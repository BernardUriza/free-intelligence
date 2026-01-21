# Desktop App Architecture (Aurity Desktop)

## Overview

Aurity Desktop es una aplicación multiplataforma construida con:
- **Frontend**: Next.js (static export)
- **Desktop Framework**: Tauri (Rust)
- **Backend Sidecar**: FastAPI (PyInstaller bundle)
- **LLM**: Ollama local

## Platforms Soportadas

| Platform | Target Triple | Package Format | Status |
|----------|--------------|----------------|--------|
| macOS | `aarch64-apple-darwin` | DMG | ✅ Producción |
| Linux | `x86_64-unknown-linux-gnu` | AppImage | ✅ Producción |
| Windows | `x86_64-pc-windows-msvc` | NSIS | ✅ Producción |

## CI/CD Workflow

**File:** `.github/workflows/build-desktop.yml`

**Trigger:**
```bash
# Build plataforma específica
gh workflow run build-desktop.yml -f platform=windows
gh workflow run build-desktop.yml -f platform=macos
gh workflow run build-desktop.yml -f platform=linux

# Build todas las plataformas
gh workflow run build-desktop.yml -f platform=all
```

**Jobs disponibles:**
- `build-linux` - Ubuntu 22.04 runner
- `build-macos` - macOS ARM64 runner
- `build-windows` - Windows Server 2022 runner

## Flujo de Build (Windows)

```yaml
1. Setup:
   - Node 20 + pnpm 9
   - Rust (target: x86_64-pc-windows-msvc)
   - Python 3.14

2. Build Backend:
   - PyInstaller con spec pre-configurado
   - Output: aurity-backend-x86_64-pc-windows-msvc.exe

3. Build Frontend:
   - Next.js static export con env vars de Auth0

4. Build Tauri:
   - Compila Rust app + bundle NSIS
   - Output: Aurity_1.0.0_x64-setup.nsis.zip

5. Signing (Ed25519):
   - pnpm tauri signer sign *.nsis.zip
   - Output: *.nsis.zip.sig

6. Distribución:
   - Upload a GitHub Artifacts
   - Create GitHub Release
   - Generate updater manifest (windows-x86_64)
```

## Code Signing

**Método:** Ed25519 (cross-platform, zero cost)

**Ventajas:**
- ✅ Mismo signing key para macOS/Linux/Windows
- ✅ Zero cost (vs $200-400/año certificado tradicional)
- ✅ CI/CD compatible (GitHub Secrets)

**Trade-offs:**
- ⚠️ SmartScreen warnings en Windows (primera instalación)
- ✅ Bypass simple: "More info" → "Run anyway"
- ✅ Auto-updater funciona sin warnings después de primera instalación

**Secretos requeridos:**
- `TAURI_SIGNING_PRIVATE_KEY` - Ed25519 key (ya existe, reutilizado)

## Auto-Updater

El updater manifest (`aurity-desktop-updater.json`) se genera automáticamente con 3 platforms:

```json
{
  "version": "1.0.0",
  "platforms": {
    "darwin-aarch64": { "signature": "...", "url": "..." },
    "linux-x86_64": { "signature": "...", "url": "..." },
    "windows-x86_64": { "signature": "...", "url": "..." }
  }
}
```

La app detecta updates en background y notifica al usuario.

## Local Development (Windows)

```powershell
# Build backend
cd apps/aurity-desktop/pyinstaller
python -m PyInstaller aurity-backend-x86_64-pc-windows-msvc.spec

# Build Tauri
cd ..
pnpm install
pnpm tauri build --target x86_64-pc-windows-msvc

# Verificar output
dir src-tauri\target\x86_64-pc-windows-msvc\release\bundle\nsis\
```

## Troubleshooting

**Windows Build Failures:**
- PyInstaller: Verificar que `backend/requirements-prod.txt` esté actualizado
- NSIS: Verificar que `tauri.conf.json` tenga config de Windows (líneas 88-101)
- Signing: Verificar que `TAURI_SIGNING_PRIVATE_KEY` esté en GitHub Secrets

**SmartScreen Bypass:**
- Normal con Ed25519 signing
- Documentado en README con screenshots
- Hash SHA256 incluido en release notes para verificación

## Archivos Críticos

| Archivo | Propósito |
|---------|-----------|
| `.github/workflows/build-desktop.yml` | CI/CD pipeline (3 platforms) |
| `apps/aurity-desktop/src-tauri/tauri.conf.json` | Tauri config (NSIS settings líneas 88-101) |
| `apps/aurity-desktop/pyinstaller/aurity-backend-x86_64-pc-windows-msvc.spec` | PyInstaller config Windows |
| `apps/aurity-desktop/README.md` | User-facing build instructions |

**Ver también:** `.claude/rules/ci-cd/windows-builds.md` para debugging journey detallado
