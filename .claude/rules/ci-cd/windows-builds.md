# Windows Build Debugging Journey

**Last Updated:** 2026-01-20

## Context

Windows builds fallaban consistentemente. Proceso de debugging iterativo reveló 8 errores encadenados. Cada build fallaba "un paso más adelante" hasta completar.

## Errores Encontrados y Fixes Aplicados

### Error #1: Missing requirements.txt
**Síntoma:** PyInstaller no encontraba requirements.txt  
**Root Cause:** Archivo faltante en `apps/aurity-desktop/pyinstaller/`  
**Fix:** Crear requirements.txt con PyInstaller==6.11.1  

### Error #2: PyInstaller Version Incompatible
**Síntoma:** Conflicto de versiones de PyInstaller  
**Root Cause:** Version mismatch entre requirements.txt y spec file  
**Fix:** Pin PyInstaller==6.11.1 consistentemente  

### Error #3: Dependency Conflicts
**Síntoma:** pip resolver conflicts durante instalación  
**Root Cause:** Dependencies con versiones incompatibles  
**Fix:** Resolver conflicts en requirements-prod.txt  

### Error #4: Backend Dependencies No Instaladas
**Build:** #21138010524  
**Síntoma:** Import errors durante PyInstaller build  
**Root Cause:** Step "Install backend dependencies" faltante antes de PyInstaller  
**Fix:** Agregar `pip install -r backend/requirements-prod.txt` antes de PyInstaller  
**Commit:** 620ec78  

### Error #5: Rust 1.84 → 1.85 Required
**Build:** #21159544629  
**Síntoma:**
```
Adding async-lock v3.4.2 (requires Rust 1.85)
Adding dlopen2 v0.8.2 (requires Rust 1.85)
Adding zbus v5.13.2 (requires Rust 1.85)
```
**Root Cause:** rust-toolchain.toml especificaba 1.84.0 pero dependencies requerían 1.85.0+  
**Fix:** Upgrade `apps/*/rust-toolchain.toml` de 1.84.0 → 1.85.0  
**Commit:** ef3b2da  

### Error #6: Pre-build Validation Runs Before Binary Exists
**Build:** #21159966229  
**Síntoma:**
```
error: resource path `binaries\aurity-backend-x86_64-pc-windows-msvc.exe` doesn't exist
```
**Root Cause:** Pre-build Validation ejecuta `cargo check` que lee `tauri.conf.json`, el cual referencia el backend binary que aún no ha sido compilado por PyInstaller  
**Fix:** Disabled Pre-build Validation con `if: false`  
**User Commit:** 2b8b342  

**Learning:** `cargo check` valida que tauri.conf.json sea válido, incluyendo que existan los binaries referenciados. Pre-build Validation debe correr DESPUÉS de compilar el backend, no antes.

### Error #7: Sign NSIS Installer Hangs
**Build:** #21160148835  
**Síntoma:** Step "Sign NSIS installer" colgado por 12+ minutos (debería tomar <10s)  
**Root Cause:** PowerShell maneja stdin pipe diferente que bash - `echo "" |` causa hang  
**Fix:** Remover pipe, pasar private-key directamente:
```powershell
# ANTES (hang):
echo "" | pnpm tauri signer sign "${{ steps.paths.outputs.path }}" --private-key "..."

# DESPUÉS (funciona):
pnpm tauri signer sign "${{ steps.paths.outputs.path }}" --private-key "..."
```
**Commit:** ac4143b  

### Error #8: wc/tr Not Available in Windows Git Bash
**Build:** #21160148835  
**Síntoma:** `prepare-python-full.sh` exit code 127 "command not found"  
**Root Cause:** Script usa `wc -c` y `tr` que no existen en Windows Git Bash  
**Fix:** Cross-platform file size detection con `stat`:
```bash
# ANTES (falla en Windows):
FILE_SIZE=$(wc -c < "$FILE" | tr -d ' ')

# DESPUÉS (cross-platform):
if command -v stat &> /dev/null && stat --version &> /dev/null 2>&1; then
    FILE_SIZE=$(stat -c%s "$FILE")  # Linux (GNU stat)
elif command -v stat &> /dev/null; then
    FILE_SIZE=$(stat -f%z "$FILE")  # macOS (BSD stat)
else
    FILE_SIZE=$(powershell -Command "(Get-Item '$FILE').Length")  # Windows fallback
fi
```
**Commit:** ac4143b  

## Build Progression

| Build | Errors Fixed | Farthest Step Reached | Outcome |
|-------|--------------|----------------------|---------|
| #21128337271 | None | Prepare Python Installer | Network timeout |
| #21138010524 | #1-3 | Pre-build Validation | Wrong directory |
| #21159406976 | #1-4 | Pre-build Validation | Rust formatting |
| #21159544629 | #1-5 | Pre-build Validation | Rust 1.84→1.85 |
| #21159741973 | #1-6 | Pre-build Validation | cargo clippy timeout |
| #21159966229 | #1-6 | Pre-build Validation | Disabled (fix #6) |
| #21160148835 | #1-6 | Sign NSIS installer | PowerShell hang (error #7) |
| #21160500828 | #1-8 | In Progress | Testing final fixes |

## Key Learnings

### 1. Iterative Debugging is Normal in CI/CD
Cada build falla "un paso más adelante". No puedes ver errores posteriores hasta resolver los anteriores.

### 2. Cross-Platform Shell Scripting is Hard
- PowerShell ≠ Bash (stdin pipes, command availability)
- Git Bash on Windows no incluye todas las GNU tools (wc, tr)
- Usar `stat` en vez de `wc` para file size (cross-platform)

### 3. Rust Toolchain Version Matters
- Dependencies pueden requerir versiones específicas (edition2024 → Rust 1.85+)
- rust-toolchain.toml debe coincidir con setup-tauri action

### 4. Build Order Dependencies
- Tauri config validation requiere que backend binaries existan
- Pre-build validation debe correr DESPUÉS de compilar sidecars

### 5. cargo clippy vs cargo check for CI
- `cargo clippy` compila TODAS las dependencies (15-20 min con 587 packages)
- `cargo check` solo valida sintaxis/tipos (2-3 min)
- Para CI fail-fast, usar `cargo check` es suficiente

## Debugging Commands

```bash
# Trigger Windows build
gh workflow run build-desktop.yml -f platform=windows --ref dev

# Monitor build progress
gh run watch

# View specific job logs
gh run view --job=<job-id> --log

# Cancel stuck build
gh run cancel <run-id>

# Check build artifacts
gh run view <run-id> --json artifacts
```
