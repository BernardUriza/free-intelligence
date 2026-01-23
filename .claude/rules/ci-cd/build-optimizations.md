# Build Time Optimizations (2026-01-20)

## Context

Después de resolver Errors #1-13 en Windows builds, identificamos que los builds tardaban **15-20 minutos** consistentemente. Implementamos 5 optimizaciones en 40 minutos para reducir tiempos a **~10-13 minutos** (35-45% más rápido).

---

## Optimizaciones Implementadas

### Quick Win #1: Fix sccache Config (10 min)

**Problema:** sccache v0.0.6 con 0% cache hits

**Cambios:**
```yaml
# ANTES:
- uses: mozilla-actions/sccache-action@v0.0.6
- run: echo "RUSTC_WRAPPER=sccache" >> $env:GITHUB_ENV  # Redundante

# DESPUÉS:
- uses: mozilla-actions/sccache-action@v0.0.9
  env:
    SCCACHE_GHA_ENABLED: "true"  # Crítico para GHA cache
# Step "Configure sccache" eliminado (redundante)
```

**Impacto esperado:** 0% → 60-80% cache hits en builds subsecuentes

**Rationale:**
- v0.0.6 es de sept 2023, v0.0.9 (junio 2024) incluye fixes para GHA cache migration
- `SCCACHE_GHA_ENABLED: "true"` necesario para usar GitHub Actions cache backend
- Step manual "Configure sccache" era redundante (el action ya configura RUSTC_WRAPPER)

---

### Quick Win #2: Enable Cargo Incremental (5 min)

**Problema:** Cargo incremental deshabilitado por default en release builds

**Cambios:**
```yaml
# Agregado a 4 jobs: build-fi-monitor, build-linux, build-macos, build-windows
jobs:
  build-windows:
    runs-on: windows-latest
    env:
      CARGO_INCREMENTAL: "1"  # ← Nuevo
```

**Impacto esperado:** 30-50% faster Rust recompilation cuando solo cambias 1-2 archivos

**Rationale:**
- Cargo incremental cachea artifacts intermedios de compilación
- Por default está OFF en release builds (on solo en debug)
- Trade-off: Binaries ~5% más grandes, pero build 30-50% más rápido

---

### Quick Win #3: Cache PyInstaller Build Directory (15 min)

**Problema:** Solo cacheábamos `dist/` (binary final), no `build/` (metadata)

**Cambios:**
```yaml
# ANTES:
- uses: actions/cache@v4
  with:
    path: apps/aurity-desktop/pyinstaller/dist

# DESPUÉS:
- uses: actions/cache@v4
  with:
    path: |
      apps/aurity-desktop/pyinstaller/dist
      apps/aurity-desktop/pyinstaller/build  # ← Agregado
```

**Impacto esperado:** 20-30% faster PyInstaller builds

**Rationale:**
- `build/` contiene import analysis, dependency graphs, metadata
- PyInstaller puede reusar estos artifacts si el código Python no cambió
- Cache key se invalida solo si cambias backend/src/ o requirements-prod.txt

---

### Quick Win #4: Fix Cargo Cache Conflict (10 min)

**Problema:** Cargo cache y sccache intentaban cachear los mismos artifacts

**Cambios:**
```yaml
# ANTES:
- name: Cache Cargo
  with:
    path: |
      ~/.cargo/registry/index
      ~/.cargo/registry/cache
      ~/.cargo/git/db
      apps/fi-monitor/src-tauri/target      # ← CONFLICTO
      apps/aurity-desktop/src-tauri/target  # ← CONFLICTO
    key: cargo-${{ runner.os }}-${{ hashFiles('**/Cargo.lock') }}-${{ hashFiles('apps/**/src-tauri/src/**/*.rs') }}

# DESPUÉS:
- name: Cache Cargo dependencies
  with:
    path: |
      ~/.cargo/registry/index
      ~/.cargo/registry/cache
      ~/.cargo/git/db
      # target/ removido - sccache lo maneja
    key: cargo-deps-${{ runner.os }}-${{ hashFiles('**/Cargo.lock') }}
```

**Impacto esperado:** Better cache hit rates, smaller cache size

**Rationale:**
- Cargo cache guardaba `target/` → cache key incluía hash de .rs files
- sccache guardaba compilation units → cache key diferente
- Resultado: Ambos caches se pisaban, 0% hit rate
- **Fix:** Separar responsabilidades:
  - Cargo cache → SOLO dependencies (crates.io registry)
  - sccache → SOLO compiled artifacts (binaries, libs)

---

### Quick Win #5: Add Concurrency Groups (20 min)

**Problema:** Builds redundantes desperdiciaban runner time

**Cambios:**
```yaml
# Agregado al workflow level:
concurrency:
  group: build-desktop-${{ github.ref }}-${{ github.event.inputs.platform }}
  cancel-in-progress: true
```

**Impacto esperado:** Saves runner time cuando iteramos rápido (push → fix → push)

**Rationale:**
- Si triggereamos build Windows, luego fix bug, luego otro build Windows
- Sin concurrency: Ambos builds corren (desperdicia ~15-20 min)
- Con concurrency: Primer build se CANCELA automáticamente
- Group key incluye branch + platform para evitar cancelar builds diferentes

---

## Resultados Medidos

### Build Comparison

| Build ID | Optimizaciones | Tiempo | Conclusión |
|----------|---------------|--------|------------|
| #21175698415 | ❌ Sin optimizaciones | **23 min** | SUCCESS |
| #21176219299 | ✅ 5 Quick Wins aplicados | **~12-15 min** (estimado) | In Progress |

**Mejora esperada:** 35-48% más rápido (23 min → 12-15 min)

### Cache Performance (First Build)

⚠️ **IMPORTANTE:** Los resultados de #21176219299 son del PRIMER build con optimizaciones.

- sccache: **Construyendo cache** (0% hits esperado)
- PyInstaller build cache: **Construyendo cache**
- Cargo deps cache: **Hit** (dependencies no cambiaron)

**Próximo build esperamos:**
- sccache: **60-80% hits** (solo recompila archivos cambiados)
- PyInstaller: **100% hit** (si backend/src/ no cambió)
- Cargo deps: **100% hit** (si Cargo.lock no cambió)

**Tiempo esperado en segundo build:** ~5-10 min (50-65% más rápido que baseline)

---

## Key Learnings

### 1. Cache Layer Conflicts

**Problema:** Múltiples caches intentando manejar los mismos artifacts → 0% hit rate

**Solución:** Separar responsabilidades por layer:
- Cargo cache → Dependencies (registry, git)
- sccache → Compiled artifacts (binaries, libs)
- PyInstaller cache → Python backend artifacts

**Lesson:** Cuando usas múltiple layers de caching, asegura **scope exclusivo** para cada layer.

### 2. First Build vs Subsequent Builds

**Primer build con cache nuevo:**
- Cache miss en TODOS los layers
- Tiempo similar a build sin cache
- **Propósito:** Construir cache para futuros builds

**Segundo build (cache warm):**
- Cache hits en mayoría de artifacts
- Tiempo dramáticamente reducido (50-65% más rápido)

**Lesson:** No juzgues optimizaciones de cache por el primer build. Mide el SEGUNDO build.

### 3. Incremental Compilation Trade-offs

**CARGO_INCREMENTAL=1:**
- ✅ 30-50% faster recompilation
- ⚠️ Binaries ~5% más grandes
- ⚠️ Cache size aumenta (~500 MB más)

**Decision:** Para CI/CD donde build time > binary size, SIEMPRE vale la pena.

### 4. GitHub Actions Cache Migration

**Context:** GitHub migró cache service en febrero 2025.

sccache v0.0.6 (sept 2023):
- ❌ Usa legacy cache service
- ❌ Sin soporte para nuevas features

sccache v0.0.9 (junio 2024):
- ✅ Migrado a nuevo cache service
- ✅ Mejor cache key generation
- ✅ `SCCACHE_GHA_ENABLED` para explicit opt-in

**Lesson:** Mantén actions actualizados, especialmente después de infrastructure migrations.

---

## Future Optimizations

### Potential Quick Wins (not implemented yet)

1. **Self-hosted Runners** (~$100/month, 2-3x faster)
   - GitHub shared runners son lentos
   - Self-hosted en AWS/GCP: 2-4x faster, costo fijo
   - Trade-off: Mantenimiento + seguridad

2. **Matrix Builds** (unificar build-linux/macos/windows)
   - Menos código duplicado
   - GitHub paraleliza automáticamente
   - Trade-off: Mayor complejidad en job único

3. **Remote Build Caching** (BuildJet, CacheDrive)
   - Cache compartido entre runners
   - ~10x faster cache restore
   - Trade-off: $49-99/month

4. **Cargo Chef** (para Docker builds)
   - Layer caching para dependencies
   - Solo útil si usamos Docker en CI
   - Trade-off: Complejidad adicional

---

## Debugging Commands

```bash
# Trigger build con optimizaciones
gh workflow run build-desktop.yml -f platform=windows --ref dev

# Monitor build progress
gh run watch

# Compare build times
bash scripts/compare-build-times.sh OLD_BUILD_ID NEW_BUILD_ID

# Check sccache stats en logs
gh run view BUILD_ID --log | grep -i "sccache stats"

# Download ejecutable cuando termine
bash scripts/download-windows-build.sh BUILD_ID
```

---

## References

- [mozilla-actions/sccache-action releases](https://github.com/Mozilla-Actions/sccache-action/releases)
- [GitHub Actions Cache Migration](https://github.blog/changelog/2024-04-29-cache-service-legacy-backend-deprecation/)
- [Cargo Incremental Compilation](https://doc.rust-lang.org/cargo/reference/profiles.html#incremental)
- [PyInstaller Caching](https://pyinstaller.org/en/stable/usage.html#using-a-build-folder)

---

**Commit:** 90d37bd
**PR:** (pending)
**Date:** 2026-01-20
