# Version Management (Single Source of Truth)

**Last Updated:** 2026-01-27
**Status:** ✅ Implemented

---

## Problem Statement

Before this implementation, version chaos existed across the codebase:

### fi-monitor (4 different versions):
```
tauri.conf.json → 1.0.6 ✅
Cargo.toml      → 1.0.2 ❌
package.json    → 1.0.0 ❌ (SUPER desincronizado)
UPDATER-SETUP.md→ 1.0.1 ❌ (doc obsoleta)
```

### aurity-desktop (3 different versions):
```
tauri.conf.json → 1.0.6 ✅
Cargo.toml      → 1.0.2 ❌
package.json    → 1.0.2 ❌
```

**Impact:**
- Cargo build showed 1.0.2
- npm/pnpm showed different versions
- NSIS installer said 1.0.6
- Total confusion for developers and users
- CI/CD could generate artifacts with mismatched metadata

---

## Solution Design

**Single Source of Truth:** `apps/*/src-tauri/tauri.conf.json`

### Why tauri.conf.json?

1. **CI/CD already reads from it** - `get-artifact-path.js` line 78
2. **Tauri bundler requires it** - Metadata for installers (NSIS, DMG, AppImage)
3. **No circular dependencies** - Cargo.toml and package.json don't affect Tauri build
4. **Semantically correct** - It IS the version of the desktop app
5. **Authoritative** - Tauri is the framework, its config should be truth

### Architecture

```
Source of Truth: tauri.conf.json (fi-monitor + aurity-desktop)
         ↓
    ┌────┴────┐
    ↓         ↓
package.json  Cargo.toml
(auto-sync)   (auto-sync)
```

---

## Implementation

### Files Created

1. **`scripts/sync-versions.js`** (286 lines)
   - Reads versions from both apps' tauri.conf.json
   - Updates package.json (JSON parse/stringify)
   - Updates Cargo.toml (regex replace)
   - Modes: `--check` (validate) vs `--fix` (synchronize)
   - Colorful CLI output with ANSI codes

2. **`scripts/hooks/pre-commit.sh`** (16 lines)
   - Optional git hook
   - Prevents commits with version mismatch
   - Install with `pnpm version:install-hook`

### Files Modified

1. **`package.json`** (root)
   - Added 3 scripts:
     - `version:check` - Validate consistency
     - `version:sync` - Auto-sync all files
     - `version:install-hook` - Setup pre-commit hook

2. **`.github/workflows/build-desktop.yml`**
   - Added "Validate version consistency" step to 4 jobs:
     - build-fi-monitor (line ~100)
     - build-linux (line ~333)
     - build-macos (line ~471)
     - build-windows (line ~637)
   - Runs `pnpm version:check` before builds
   - Fails fast if versions mismatch

3. **`.claude/CLAUDE.md`**
   - Added "Version Management" section with quick reference

4. **`.claude/rules/development/version-management.md`** (this file)
   - Comprehensive documentation

### Synchronized Files (Initial Commit)

- `apps/fi-monitor/package.json` (1.0.0 → 1.0.6)
- `apps/fi-monitor/src-tauri/Cargo.toml` (1.0.2 → 1.0.6)
- `apps/aurity-desktop/package.json` (1.0.2 → 1.0.6)
- `apps/aurity-desktop/src-tauri/Cargo.toml` (1.0.2 → 1.0.6)

---

## Developer Workflow

### Daily Usage

**Cambiar versión:**
```bash
# 1. Editar SOLO tauri.conf.json
vim apps/fi-monitor/src-tauri/tauri.conf.json  # cambiar a 1.0.7

# 2. Sincronizar otros archivos
pnpm version:sync

# 3. Verificar
pnpm version:check  # ✅

# 4. Commit (hook valida automáticamente si está instalado)
git add .
git commit -m "chore: bump version to 1.0.7"
```

**Si olvidaste sincronizar:**
```bash
git commit -m "..."
# ❌ Version mismatch detected! (si tienes hook instalado)
# 💡 Fix with: pnpm version:sync

pnpm version:sync
git add .
git commit -m "..."  # ✅ Ahora pasa
```

### One-Time Setup (Optional)

**Install pre-commit hook:**
```bash
pnpm version:install-hook
```

This prevents committing version mismatches locally (before CI/CD catches it).

### CI/CD Workflow

**Every build automatically:**
1. Checkout código
2. **Validate version consistency** ← NEW STEP
3. Build (solo si paso 2 pasa ✅)

**If validation fails:**
- Build stops immediately (fail fast)
- Error message shows mismatched versions
- Developer must run `pnpm version:sync` and push again

---

## Script Implementation

### sync-versions.js Architecture

```javascript
// Apps to synchronize
const APPS = [
  {
    name: 'fi-monitor',
    tauriConfig: 'apps/fi-monitor/src-tauri/tauri.conf.json',
    packageJson: 'apps/fi-monitor/package.json',
    cargoToml: 'apps/fi-monitor/src-tauri/Cargo.toml'
  },
  {
    name: 'aurity-desktop',
    tauriConfig: 'apps/aurity-desktop/src-tauri/tauri.conf.json',
    packageJson: 'apps/aurity-desktop/package.json',
    cargoToml: 'apps/aurity-desktop/src-tauri/Cargo.toml'
  }
];

// Read functions
readTauriVersion(configPath)   // JSON parse → .version
readPackageVersion(packagePath) // JSON parse → .version
readCargoVersion(cargoPath)     // Regex: /^version\s*=\s*"([^"]+)"/m

// Update functions
updatePackageVersion(packagePath, newVersion)  // JSON parse → modify → stringify
updateCargoVersion(cargoPath, newVersion)      // Regex replace: /^version\s*=\s*"[^"]+"/m
```

### --check Mode

```bash
$ node scripts/sync-versions.js --check

🔍 Version Synchronization Tool
Source of Truth: apps/*/src-tauri/tauri.conf.json

Mode: Validation

✅ fi-monitor: All versions match (1.0.6)
✅ aurity-desktop: All versions match (1.0.6)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ All versions synchronized
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Exit code:**
- `0` if all versions match
- `1` if any mismatch detected

### --fix Mode

```bash
$ node scripts/sync-versions.js --fix

🔍 Version Synchronization Tool
Source of Truth: apps/*/src-tauri/tauri.conf.json

Mode: Synchronization

ℹ️  fi-monitor: Syncing to 1.0.6...
ℹ️    Updating package.json: 1.0.0 → 1.0.6
ℹ️    Updating Cargo.toml: 1.0.2 → 1.0.6
✅ fi-monitor: Synchronized to 1.0.6
ℹ️  aurity-desktop: Syncing to 1.0.6...
ℹ️    Updating package.json: 1.0.2 → 1.0.6
ℹ️    Updating Cargo.toml: 1.0.2 → 1.0.6
✅ aurity-desktop: Synchronized to 1.0.6

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ All versions synchronized
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ℹ️  Next steps:
  1. Review changes: git diff
  2. Commit: git add . && git commit -m "chore: sync versions"
```

**Exit code:**
- `0` if synchronization succeeds
- `1` if any file update fails

---

## Troubleshooting

### Error: "Failed to read tauri.conf.json"

**Causa:** Archivo no existe o JSON inválido

**Fix:**
```bash
# Verificar que el archivo existe
ls -la apps/fi-monitor/src-tauri/tauri.conf.json
ls -la apps/aurity-desktop/src-tauri/tauri.conf.json

# Validar JSON
cat apps/fi-monitor/src-tauri/tauri.conf.json | jq .
```

### Error: "Failed to update Cargo.toml"

**Causa:** Regex no match (formato inesperado)

**Fix:**
```bash
# Verificar formato de version en Cargo.toml
grep '^version' apps/fi-monitor/src-tauri/Cargo.toml

# Debe ser:
# version = "1.0.6"

# NO debe ser:
# version="1.0.6" (sin espacios)
# version = '1.0.6' (single quotes)
```

### CI/CD Fails: "Version mismatch detected"

**Causa:** Olvidaste correr `pnpm version:sync` localmente

**Fix:**
```bash
# Localmente
pnpm version:sync
git add .
git commit -m "chore: sync versions to 1.0.6"
git push origin dev
```

### Pre-commit Hook Not Working

**Causa:** Hook no instalado

**Fix:**
```bash
pnpm version:install-hook

# Verificar instalación
ls -l .git/hooks/pre-commit
# Debe ser ejecutable: -rwxr-xr-x
```

---

## Design Decisions

### Why Script Instead of External Tool?

**Pros of custom script:**
- ✅ Zero dependencies (only Node.js)
- ✅ Easy to debug and modify
- ✅ No breaking changes from external tools
- ✅ Educational (developers see the logic)
- ✅ Survives for years without maintenance

**Cons:**
- ⚠️ Must maintain ourselves
- ⚠️ Not battle-tested by community

**Decision:** Custom script wins for simplicity and longevity.

### Why Manual Hook Instead of Husky?

**Pros of manual hook:**
- ✅ No dependencies (saves 500KB)
- ✅ Opt-in explicit (developer choice)
- ✅ Cross-platform (npm/pnpm/yarn/bun)
- ✅ No complex configuration
- ✅ Works with monorepo structure

**Cons:**
- ⚠️ Developers must remember to install
- ⚠️ Not automatic like Husky

**Decision:** Manual wins for zero dependencies and simplicity.

### Why CI/CD Validation?

**Pros:**
- ✅ Gate final (hook is convenience)
- ✅ Catches ALL mistakes before artifacts
- ✅ Fail fast (ahorra build time)
- ✅ Error messages clear
- ✅ No way to bypass

**Cons:**
- None

**Decision:** CI/CD validation is mandatory (hook is optional).

---

## Future Enhancements

### Potential Improvements

1. **Auto-sync on tauri.conf.json change**
   - File watcher that triggers sync automatically
   - Requires adding fs.watch() or chokidar

2. **Version bump commands**
   - `pnpm version:bump:patch` (1.0.6 → 1.0.7)
   - `pnpm version:bump:minor` (1.0.6 → 1.1.0)
   - `pnpm version:bump:major` (1.0.6 → 2.0.0)
   - Updates tauri.conf.json then syncs

3. **Multi-app version management**
   - Currently fi-monitor and aurity-desktop have independent versions
   - Could enforce they match (if desired)

4. **Changelog generation**
   - Auto-generate CHANGELOG.md entries on version bump
   - Integrate with conventional commits

### Not Planned (YAGNI)

- ❌ Support for pre-release versions (1.0.6-beta.1)
- ❌ Support for build metadata (1.0.6+build.123)
- ❌ Version rollback mechanism
- ❌ Version history tracking

If needed, add these incrementally.

---

## Testing Checklist

### After Installation

```bash
# 1. Script funciona
pnpm version:check  # Debe pasar ✅

# 2. Sync es idempotente
pnpm version:sync   # No changes (already synced)

# 3. Hook instala correctamente
pnpm version:install-hook
ls -l .git/hooks/pre-commit  # Debe existir y ser ejecutable

# 4. Hook previene commits malos (test)
echo '{"version": "1.0.5"}' > test.json
git add test.json
git commit -m "test"  # DEBE FALLAR con error de version mismatch

# 5. Limpiar test
git reset HEAD test.json
rm test.json

# 6. Verificar todas las versiones
grep -r "version.*1\.0\.[0-9]" apps/fi-monitor/ --include="*.json" --include="*.toml" | grep -v node_modules
# TODAS deben mostrar 1.0.6

grep -r "version.*1\.0\.[0-9]" apps/aurity-desktop/ --include="*.json" --include="*.toml" | grep -v node_modules
# TODAS deben mostrar 1.0.6
```

---

## Success Criteria

This implementation is successful if:

1. ✅ Developers only edit `tauri.conf.json` for version changes
2. ✅ CI/CD catches ALL version mismatches (0 artifacts with mismatch)
3. ✅ One command fixes issues: `pnpm version:sync`
4. ✅ Script runs for years without maintenance
5. ✅ Zero confusion about "which version is correct"

---

## References

- **Plan:** `/Users/bernardurizaorozco/.claude/projects/.../8715198f-f4fc-4c35-9e02-77e330572162.jsonl`
- **Initial PR:** (pending)
- **Commits:**
  - e09bc22: Initial synchronization + script
  - 6617584: Add pnpm commands
  - 5d75460: CI/CD integration
  - 4bb0f22: Pre-commit hook

---

**Implementation completed successfully on 2026-01-27.**
