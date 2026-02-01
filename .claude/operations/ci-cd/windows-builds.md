# Windows Build Debugging Journey

**Last Updated:** 2026-01-21 (Errors #1-17 documented)

## Context

Windows builds fallaban consistentemente. Proceso de debugging iterativo reveló **17 errores encadenados** a través de 3 días. Cada build fallaba "un paso más adelante" hasta completar.

**Timeline:**
- **Day 1 (2026-01-19):** Errors #1-10 - Infrastructure setup (PyInstaller, Rust, signing, NSIS template)
- **Day 2 (2026-01-20):** Errors #11-16 - Configuration issues (template includes, path escaping, artifact naming, email SMTP)
- **Day 3 (2026-01-21):** Error #17 - Cross-platform compatibility (fcntl → portalocker)

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

### Error #9: Signing Still Hangs (Timestamp Server Timeout)
**Build:** #21160500828 (both build-fi-monitor and build-windows hung)
**Síntoma:** Build colgado 19+ minutos en "Sign NSIS installer" a pesar de Fix #7
**Root Cause:** Fix #7 resolvió PowerShell stdin pipe hang, pero Tauri signer TODAVÍA espera timestamp servers externos (timestamp.digicert.com, etc.) que timeout o son lentos
**Web Research:** Timestamp servers pueden tardar 30+ segundos o timeout completamente durante peak hours
**Fix #9 (Workaround):** Agregar timeout + continue-on-error para no bloquear build:
```yaml
- name: Sign NSIS installer
  timeout-minutes: 2          # Kill si tarda >2 min
  continue-on-error: true     # No bloquear build si falla
  working-directory: apps/fi-monitor
  shell: pwsh
  run: |
    pnpm tauri signer sign "${{ steps.paths.outputs.path }}" --private-key "${{ secrets.TAURI_SIGNING_PRIVATE_KEY }}"
```
**Commit:** 23f255e
**Outcome:** Build continúa con unsigned binary (funcional para pilotos), signing manual después

**Fix #10A (Permanent Solution - Disable Timestamp Server):**
**Problem:** Fix #9 es workaround (desperdicia 2 minutos intentando signing que fallará)
**Solution:** Deshabilitar timestamp server completamente:
```json
// apps/fi-monitor/src-tauri/tauri.conf.json:57
// apps/aurity-desktop/src-tauri/tauri.conf.json:91
{
  "windows": {
    "timestampUrl": null  // ANTES: "" (empty string)
  }
}
```
**Commit:** 3babf5c

**Critical Insight - `null` vs `""`:**
- `""` (empty string) → Tauri intenta usar timestamp server default (timestamp.digicert.com)
  - Resultado: Network request que puede tardar 30+ segundos o timeout
  - CI/CD depende de disponibilidad de servidor externo
- `null` → Tauri omite timestamp completamente
  - Resultado: Signing instantáneo con Ed25519 key (sin network dependency)
  - Binary tiene misma SmartScreen warning que con `""` (no hay diferencia práctica)
- **Beneficio Fix #10A:** Ahorra 2-4 minutos por build, elimina network dependency

**SmartScreen Bypass (User Experience):**
- Pilot users ven warning: "Windows protected your PC"
- Click "More info" → "Run anyway" (2 clicks)
- Después de primera instalación, auto-updater funciona sin warnings
- Hash SHA256 incluido en release notes para verificación manual

### Error #10: NSIS Installer Duplicate HWND_BROADCAST Definition
**Build:** #21160908609 (3 retry attempts all failed)
**Síntoma:**
```
!define: "HWND_BROADCAST" already defined!
Error in script "...\installer.nsi" on line 9 -- aborting creation process
failed to bundle project `The system cannot find the file specified. (os error 2)`
```
**Root Cause:** Tauri bundler defines HWND_BROADCAST in base NSIS script FIRST, then includes custom template. The `!ifndef` guard doesn't work because definition already exists at template processing time.
**Progress:** ✅ PyInstaller, ✅ Rust compilation (11m 46s attempt 1, 2m 25s attempt 2, 0.88s attempt 3), ✅ MSI created, ❌ NSIS fails on all 3 attempts
**Failed Fix:** Tried `!ifndef HWND_BROADCAST` guard - didn't work because Tauri defines it before processing template
**Real Fix (commit f2d783c):** Remove HWND_BROADCAST definition completely from template - Tauri already provides it:
```nsis
# BEFORE (caused error):
!ifndef HWND_BROADCAST
  !define HWND_BROADCAST 0xFFFF
!endif

# AFTER (fix):
# Note: HWND_BROADCAST (0xFFFF) is provided by Tauri's bundler
# (definition removed - only keep WM_SETTINGCHANGE)
```
**File:** `apps/aurity-desktop/src-tauri/installer-template.nsi:8-12`
**Lesson:** Template processing order matters - Tauri's base definitions come BEFORE custom template inclusion

### Error #11: NSIS Template Include Errors
**Build:** #21174027116 (2026-01-20, both build-fi-monitor and build-windows failed)
**Síntoma:**
```
Error in script "...\installer.nsi" on line 11 -- aborting creation process
failed to bundle project `The system cannot find the file specified. (os error 2)`
```
**Root Cause:** Custom template `apps/aurity-desktop/src-tauri/installer-template.nsi` used `!include` statements for .nsh files (MUI2.nsh, FileFunc.nsh, LogicLib.nsh) that don't exist in Tauri bundle directory. Tauri bundler doesn't copy these dependencies when processing custom templates.
**Fix:** Remove custom template entirely, use Tauri default template (commit 756350e):
```bash
# Delete custom template
rm apps/aurity-desktop/src-tauri/installer-template.nsi

# Remove template reference from tauri.conf.json
# BEFORE:
"nsis": {
  "template": "installer-template.nsi",
  ...
}

# AFTER:
"nsis": {
  ...  # Use Tauri default template
}
```
**Rationale:** Custom template only added Python installation logic (no longer needed). Tauri default template is battle-tested and has zero external dependencies.
**Lesson:** Prefer Tauri defaults over custom templates unless absolutely necessary. Custom templates add complexity and can break across Tauri versions.

### Error #12: PowerShell Path Escaping with Spaces
**Build:** #21174027116 (signing step hung with "Terminate batch job (Y/N)?")
**Síntoma:**
```
pnpm tauri signer sign "src-tauri/.../FI Monitor_1.0.1_x64-setup.nsis.zip"
Signing without password.
Terminate batch job (Y/N)?
[timeout after 2 minutes]
```
**Root Cause:** `productName: "FI Monitor"` (with space) → path con espacio → PowerShell corrupts path escaping across GitHub Actions shell layers, even with proper quoting. Tauri signer receives malformed path and prompts for interactive confirmation.
**Fix:** Remove space from productName (commit 7f48435):
```json
// apps/fi-monitor/src-tauri/tauri.conf.json
"productName": "FIMonitor",  // BEFORE: "FI Monitor"
```
**Trade-offs:**
- ✅ Eliminates shell escaping hell
- ✅ Works across ALL shells (PowerShell, Bash, CMD)
- ⚠️ Changes installer display name (cosmetic only)
**Lesson:** NEVER use spaces in file/product names for CI/CD. Shell escaping is unreliable when paths pass through multiple layers (PowerShell → CMD → node → pnpm → Tauri).

### Error #13: NSIS Artifact Filename Wrong
**Build:** #21174027116 (artifact upload failed: "No files were found")
**Síntoma:**
```
Warning: No files were found with the provided path:
  apps/fi-monitor/.../FIMonitor_1.0.1_x64-setup.nsis.zip
```
**Root Cause:** `get-artifact-path.js` expected `.nsis.zip` but Tauri 2.0 NSIS bundler generates `.exe` directly. The `.nsis.zip` format only exists when updater plugin is active AND has valid pubkey (creates ZIP archives for auto-updates).
**Evidence from build logs:**
```
Tauri generated: FIMonitor_1.0.1_x64-setup.exe
Workflow expected: FIMonitor_1.0.1_x64-setup.nsis.zip  ← DOESN'T EXIST
```
**Fix:** Correct artifact filename (commit 7a98764):
```javascript
// apps/aurity-desktop/scripts/get-artifact-path.js
const artifacts = {
  nsis: `${productName}_${version}_x64-setup.exe`,  // BEFORE: .nsis.zip
  dmg: `${productName}_${version}_aarch64.dmg`,
  appimage: `${productName}_${version}_amd64.AppImage`
};
```
**References:**
- [Tauri Windows Installer Docs](https://v2.tauri.app/distribute/windows-installer/)
- [Tauri Updater Plugin](https://v2.tauri.app/plugin/updater/)

**Lesson:** When tools generate different outputs based on configuration, ALWAYS verify active config before assuming which files exist. Don't trust documentation examples blindly.

### Error #14: Artifact Upload Path Incorrect (Part 2)
**Build:** #21176219299 (2026-01-20, both build-windows succeeded but artifact missing)
**Síntoma:**
```
gh api "repos/.../artifacts" returns: fi-monitor-windows-nsis
Missing: aurity-windows-nsis
```
**Root Cause:** Error #13 fixed `get-artifact-path.js` to use `.exe`, but build-windows workflow still hardcoded `*.nsis.zip` in upload path. Tauri generated `Aurity_1.0.0_x64-setup.exe` but workflow tried to upload non-existent `*.nsis.zip`.
**Fix:** Update artifact upload paths (commit 9802fe5):
```yaml
# apps/aurity-desktop upload (build-windows job)
# BEFORE:
path: apps/aurity-desktop/.../nsis/*.nsis.zip

# AFTER:
path: apps/aurity-desktop/.../nsis/*.exe
```
**Files Changed:**
- `.github/workflows/build-desktop.yml` lines 791, 798
- `scripts/download-windows-build.sh` (buscar .exe no .nsis.zip)

**Related:** Error #13 (same root cause - Tauri 2.0 output format)
**Lesson:** When fixing file paths in one place (get-artifact-path.js), grep for ALL references to that filename pattern and update consistently.

### Error #15: Email Notification Silent Failures
**Build:** #21175698415, #21176219299 (both reported email SUCCESS but user never received)
**Síntoma:** Email step completes in 1 second with "success" conclusion, but email never arrives
**Root Cause:** `continue-on-error: true` on email step masks SMTP failures (auth errors, server rejects, etc.). Action fails immediately but GitHub marks step as success.
**Evidence:**
```
Email step: started 15:04:53Z, completed 15:04:54Z (1 second)
Conclusion: success
User report: "el email sigue sin llegarme"
```
**Fix:** Remove `continue-on-error` from email step (commit bc1716f):
```yaml
# BEFORE:
- name: Send build success email notification
  continue-on-error: true  # Masks failures

# AFTER:
- name: Send build success email notification
  # REMOVED continue-on-error - want to see failures
```
**Next Steps:** Trigger build #21176985799 with fix to see actual SMTP error
**Likely Issues:**
- Azure Communication Services credentials expired/invalid
- SMTP server rejecting connection (port 587 blocked?)
- Destination email address incorrect in secrets

**Lesson:** NEVER use `continue-on-error` on notification/alert steps. Notifications failing silently defeats their purpose. Fail loudly so you know there's a problem.

### Error #16: Email Notification SSL Failure
**Build:** #21176985799
**Step:** Send build success email notification (step 22)
**Duration:** 2 segundos (failure inmediato)
**Conclusion:** FAILURE

**Síntoma:**
```
Error: F0230000:error:0A00010B:SSL routines:ssl3_get_record:wrong version number:c:\ws\deps\openssl\openssl\ssl\record\ssl3_record.c:355:
```

**Root Cause:** Incompatibilidad entre puerto SMTP y modo de cifrado:

| Configuración | Valor Actual | Problema |
|---------------|--------------|----------|
| `server_port` | 587 | Puerto STARTTLS (no SSL directo) |
| `secure` | true | Fuerza SSL inmediato |

**Qué pasó:**
1. Action intenta SSL handshake inmediato (porque `secure: true`)
2. Servidor Azure SMTP en puerto 587 responde en texto plano (STARTTLS requiere EHLO primero)
3. Cliente OpenSSL recibe texto plano cuando esperaba SSL binary → "wrong version number"

**Protocolo SMTP Correcto:**

| Puerto | Protocolo | Configuración Correcta |
|--------|-----------|------------------------|
| 587 | STARTTLS | `secure: false` + action soporta auto-upgrade |
| 465 | SSL/TLS | `secure: true` |

Azure Communication Services usa puerto 587 (STARTTLS).

**Fix (commit PENDING):** Cambiar `secure: true` → `secure: false` en workflow línea 689:
```yaml
# ANTES (INCORRECTO):
- name: Send build success email notification
  uses: dawidd6/action-send-mail@v3
  with:
    server_address: smtp.azurecomm.net
    server_port: 587
    secure: true  # ← ERROR

# DESPUÉS (CORRECTO):
- name: Send build success email notification
  uses: dawidd6/action-send-mail@v3
  with:
    server_address: smtp.azurecomm.net
    server_port: 587
    secure: false  # ← STARTTLS mode (auto-upgrade a TLS)
```

**Alternat fix:** Cambiar puerto a 465 y mantener `secure: true`, pero Azure recomienda 587.

**Verificación:** Después de aplicar fix:
1. Email step debería completar en ~5-10s (vs 2s failure)
2. Logs mostrarán conexión SMTP exitosa
3. Email llegará a `${{ secrets.NOTIFY_EMAIL }}`

**Lesson Learned:** `secure: true` NO es "más seguro" - significa "SSL desde el inicio" (puerto 465). Puerto 587 requiere `secure: false` para STARTTLS (igual de seguro, diferente handshake).

**Remover `continue-on-error` fue crítico** - sin eso, este error hubiera permanecido invisible.

### Error #17: fcntl Unix-only Module (Critical Cross-Platform Issue)
**Build:** #21194089591 (2026-01-21)
**Step:** Install backend dependencies
**Duration:** 2 minutos (failure durante PyInstaller import check)
**Conclusion:** FAILURE

**Síntoma:**
```
ModuleNotFoundError: No module named 'fcntl'
File: backend/src/fi_storage/infrastructure/hdf5/sessions_store.py, line 49
```

**Root Cause:** `fcntl` module es Unix-only (Linux/macOS), NO existe en Windows. El código lo importaba directamente:
```python
import fcntl  # ❌ Unix-only - falla en Windows
```

**Contexto del código:**
`sessions_store.py` usa file locking extensivamente en 6+ métodos:
- `_read_index()` - LOCK_SH (shared lock)
- `_write_index()` - LOCK_EX (exclusive lock)
- `create()` - LOCK_EX durante append
- `get()` - LOCK_SH durante read
- `update()` - LOCK_EX durante append
- `list()`, `count()` - LOCK_SH durante reads

Sin file locking, operations serían non-atomic → race conditions → data corruption en manifest.jsonl.

**Fix:** Reemplazar `fcntl` con `portalocker` (cross-platform alternative). Commit 2e7d845:

```python
# backend/src/fi_storage/infrastructure/hdf5/sessions_store.py (líneas 31-49)

import json
import random

# Cross-platform file locking (works on Unix + Windows)
try:
    import portalocker
    # Create fcntl-compatible module with portalocker
    class fcntl:
        LOCK_SH = portalocker.LOCK_SH
        LOCK_EX = portalocker.LOCK_EX
        LOCK_UN = portalocker.LOCK_UN

        @staticmethod
        def flock(fd, operation):
            return portalocker.lock(fd, operation)

except ImportError:
    # Fallback to fcntl on Unix systems (if portalocker not installed)
    import fcntl  # type: ignore[no-redef]
```

**Dependency added (backend/requirements-prod.txt línea 21):**
```
portalocker>=2.8.2  # Cross-platform file locking (fcntl replacement for Windows)
```

**Why wrapper class instead of direct portalocker calls:**
- ✅ Mantiene código existente sin cambios (60+ llamadas a `fcntl.flock()`)
- ✅ Compatible con Unix systems sin portalocker (fallback a fcntl nativo)
- ✅ API idéntica (`fcntl.LOCK_EX`, `fcntl.flock(fd, operation)`)
- ⚠️ Type checker warning `type: ignore[no-redef]` necesario para fallback

**Testing verification (Build #21194089591):**
1. ✅ portalocker instalado correctamente:
   ```
   Collecting portalocker>=2.8.2 (from -r backend/requirements-prod.txt (line 21))
   Downloading portalocker-3.2.0-py3-none-any.whl (22 kB)
   Collecting pywin32>=226 (from portalocker>=2.8.2...)
   Successfully installed portalocker-3.2.0 pywin32-311
   ```
2. ✅ PyInstaller build SUCCESS (backend exe compilado sin errors)
3. ✅ Tauri build SUCCESS (Aurity_1.0.0_x64-setup.exe generado)

**Artifact output:**
- `aurity-windows-nsis`: 100 MB
- SHA256: `6b0d435f2d35d1e9f01554173eb459dfbda6ee841963e1cfa008dab483365970`
- Location: `downloads/Aurity_1.0.0_x64-setup.exe`

**Key Learnings:**
1. **Unix-only modules are a common cross-platform trap:**
   - `fcntl` - file locking (Unix only)
   - `pwd`, `grp` - user/group info (Unix only)
   - `termios` - terminal I/O (Unix only)
   - `pty` - pseudo-terminal (Unix only)

2. **Cross-platform alternatives exist:**
   - fcntl → `portalocker` (file locking)
   - pwd/grp → `getpass` (user info)
   - os.fork() → `multiprocessing` (process spawning)

3. **Wrapper pattern for backward compatibility:**
   - When replacing a module, create a compatibility layer
   - Maintains existing API → minimal code changes
   - Supports both old (fcntl) and new (portalocker) implementations

4. **Dependencies matter on Windows:**
   - portalocker requires `pywin32>=226` on Windows
   - PyInstaller must bundle both portalocker + pywin32
   - Verify in logs that dependencies install correctly

5. **Why this wasn't caught earlier:**
   - macOS/Linux development → fcntl works fine
   - No Windows testing in local dev
   - CI/CD caught it during first Windows build
   - **Solution:** Cross-platform testing BEFORE CI/CD

**Related to Error #8:** Both are cross-platform issues (wc/tr vs fcntl). Pattern: Unix tools/modules don't exist on Windows. Always use cross-platform alternatives in shared code.

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
| #21160500828 | #1-8 | Sign NSIS installer | Timestamp hang (error #9) - Cancelled |
| #21160908609 | #1-9 | Build Tauri app (NSIS) | HWND_BROADCAST duplicate (error #10) |
| #21174027116 | #1-10 | Build Tauri app (NSIS) | Template include errors (error #11) |
| #21174027116 | #1-12 | Upload NSIS artifact | Artifact not found (error #13) |
| #21176219299 | #1-14 | Upload NSIS artifact | Path mismatch .nsis.zip vs .exe (error #14) |
| #21176985799 | #1-15 | Email notification | SSL/STARTTLS mismatch (error #16) - SUCCESS* |
| #21194089591 | #1-17 | Upload artifacts | **SUCCESS** - Exe generado (100 MB) |

*Build #21176985799 completó con ejecutable generado, solo email falló
**Build #21194089591 fue el PRIMER build completamente exitoso

**Journey Summary (3 Days):**
- **Day 1 (Errors #1-10):** PyInstaller → Rust → Pre-build → Signing → NSIS template
- **Day 2 (Errors #11-16):** Template includes → Path escaping → Artifact filename → Email SMTP
- **Day 3 (Error #17):** fcntl cross-platform compatibility → **SUCCESS**

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

### 6. Shell Escaping Hell with Spaces
- NEVER use spaces in productName, file paths, or artifact names for CI/CD
- PowerShell path escaping is UNRELIABLE when passing through multiple shell layers
- GitHub Actions: PowerShell → CMD → node → pnpm → tool (4+ layers)
- Solution: Use kebab-case or camelCase for all names in automation

### 7. Custom Templates = Maintenance Burden
- Tauri/framework defaults are battle-tested across versions
- Custom templates add complexity and external dependencies
- Only use custom templates when ABSOLUTELY necessary
- Document WHY custom template is needed (not just WHAT it does)

### 8. Verify Tool Output, Don't Assume
- Tools generate different files based on configuration
- Example: Tauri NSIS generates `.exe` OR `.nsis.zip` depending on updater config
- ALWAYS verify actual output files in logs before fixing "file not found" errors
- Don't trust documentation examples without verifying against your config

### 9. Two-Day Debugging Journey Pattern
- **Day 1:** Infrastructure errors (dependencies, toolchain, build order)
- **Day 2:** Configuration errors (templates, paths, artifact names)
- First wave of errors blocks second wave from being visible
- Patience and systematic iteration is required

### 10. Cross-Platform Module Compatibility
- **Common trap:** Unix-only modules (`fcntl`, `pwd`, `grp`, `termios`, `pty`)
- **Detection:** Code works on macOS/Linux but fails on Windows CI/CD
- **Solution pattern:** Wrapper classes for backward compatibility
  ```python
  try:
      import cross_platform_lib
      class unix_module:  # Wrapper
          API = cross_platform_lib.API
  except ImportError:
      import unix_module  # Fallback
  ```
- **Best practice:** Test on ALL target platforms BEFORE CI/CD
- **Quick check:** `grep -r "import fcntl\|import pwd\|import grp" backend/` → flag for review
- **Related errors:** Error #8 (wc/tr), Error #17 (fcntl) - same root cause

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
