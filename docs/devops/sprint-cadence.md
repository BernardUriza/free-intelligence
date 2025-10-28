# Sprint Cadence - Free Intelligence

**Fecha**: 2025-10-26
**Task**: FI-CICD-FEAT-002
**Sprint**: SPR-2025W44 (Sprint 2)
**Autor**: Bernard Uriza Orozco

---

## 🎯 Propósito

Establecer una **cadencia quincenal** (15 días) para sprints de Free Intelligence, con:

- ✅ Automatización de cierre de sprint
- ✅ Versionado semántico automático
- ✅ Backups con SHA256 validation
- ✅ Release notes auto-generadas
- ✅ Retención de 12 sprints (6 meses)

**Garantiza**:
- 📦 Historial completo de sprints (git bundles)
- 🏷️ Tags semánticos correlacionados con sprints
- 📝 Documentación automática de cambios
- 🔐 Integridad verificable (SHA256)
- 🗓️ Ritmo sostenible de desarrollo

---

## 📅 Cadencia de Sprint

### Duración

**15 días** (2 semanas + 1 día):
- Días laborales: 15 días consecutivos
- Horas diarias: 4h/día
- Total horas: 60h por sprint
- Sin días de descanso intermedios

### Naming Convention

```
SPR-YYYYWWW
```

**Ejemplos**:
- `SPR-2025W43` → Sprint semana 43 de 2025
- `SPR-2025W44` → Sprint semana 44 de 2025

**Cálculo de semana**:
```bash
date +%Y-W%V  # ISO week number
```

### Ciclo Completo

```
Día 0: Planning & Setup
  ├─ Crear SPRINT_X_PLAN.md
  ├─ Seleccionar cards (RICE scoring)
  ├─ Definir Definition of Done
  └─ Setup Trello board

Días 1-13: Ejecución
  ├─ 4h/día de trabajo
  ├─ Commits diarios
  ├─ Tests continuos
  └─ Actualizar SPRINT_X_TRACKER.md

Día 14: Testing & QA
  ├─ Manual testing guide
  ├─ E2E validation
  └─ Bug fixes

Día 15: Sprint Close
  ├─ Ejecutar sprint-close.sh
  ├─ Crear tag semántico
  ├─ Generar bundle backup
  ├─ Release notes
  └─ Retrospective
```

---

## 🔧 Sprint Close Automation

### Script: sprint-close.sh

**Ubicación**: `scripts/sprint-close.sh`

**Funcionalidad**:
1. Determinar versión automática (semantic versioning)
2. Generar release notes desde commits
3. Crear tag git anotado
4. Generar bundle backup (.bundle)
5. Calcular SHA256 del bundle
6. Aplicar retención (últimos 12 bundles)
7. Actualizar claude.md con entrada de cierre

### Uso Básico

```bash
# DRY RUN (recomendado primero)
./scripts/sprint-close.sh SPR-2025W44 DRY_RUN

# EXECUTE (aplicar cambios)
./scripts/sprint-close.sh SPR-2025W44 EXECUTE
```

### Output

```
🎯 Sprint Close - SPR-2025W44
Mode: EXECUTE
Timestamp: 2025-11-09 23:59 (America/Mexico_City)

📌 Step 1: Determinando versión...
  Último tag: v0.2.0
  Commits desde tag: 47
  Nueva versión: v0.3.0

📝 Step 2: Generando notas de versión...
  Notas guardadas en: backups/release-notes-v0.3.0.md

🏷️  Step 3: Creando tag v0.3.0...
  Tag v0.3.0 creado ✅

💾 Step 4: Generando bundle backup...
  Bundle creado: backups/fi-SPR-2025W44-v0.3.0-2025-11-09.bundle (5.2M)
  SHA256: a3f2d8e9b1c4...
  SHA256 guardado en: backups/SPR-2025W44-v0.3.0.sha256

🗑️  Step 5: Aplicando retención (últimos 12 bundles)...
  Bundles actuales: 3
  Retención: No necesaria (< 12 bundles)

📖 Step 6: Actualizando claude.md...
  Entrada de cierre agregada a claude.md ✅

✅ Sprint cerrado exitosamente
```

---

## 📦 Versionado Semántico

### Estrategia

Free Intelligence usa **Semantic Versioning 2.0** con modificación para sprints:

```
vMAJOR.MINOR.PATCH[-TIER]
```

**Incrementos**:
- **MAJOR**: Cambios breaking (arquitectura, APIs públicas)
- **MINOR**: Sprint completo (cada 15 días)
- **PATCH**: Hotfixes entre sprints

**Tags especiales**:
- `v0.2.0-tier1-security` → Sprint 2 Tier 1 (seguridad completada)
- `v0.3.0` → Sprint 2 completo
- `v1.0.0` → Primera versión pública (Fase 1 completa)

### Ejemplos

```
v0.1.0   → Sprint 1 (fundamento operativo)
v0.2.0   → Sprint 2 (seguridad + políticas)
v0.3.0   → Sprint 3 (observabilidad)
v0.4.0   → Sprint 4 (API HTTP)
v1.0.0   → Free Intelligence Fase 1 completa
v1.1.0   → Sprint 6 (UI React)
v2.0.0   → Fase 2 (breaking: multi-user)
```

### Auto-increment

El script `sprint-close.sh` **incrementa automáticamente MINOR**:

```bash
# Detecta último tag
LAST_TAG=$(git describe --tags --abbrev=0)

# Cuenta commits desde tag
COMMITS_SINCE=$(git rev-list ${LAST_TAG}..HEAD --count)

# Si hay commits, incrementa MINOR
if [ "$COMMITS_SINCE" -gt 0 ]; then
    MINOR=$((MINOR + 1))
    NEW_TAG="v${MAJOR}.${MINOR}.0"
fi
```

---

## 🗂️ Backups & Retención

### Git Bundles

**Qué es un git bundle**:
- Archivo único con todo el repositorio git
- Permite restaurar repo completo offline
- Incluye: commits, branches, tags, history

**Por qué usar bundles**:
- ✅ Backup autosuficiente (no requiere GitHub)
- ✅ Portabilidad total (un solo archivo)
- ✅ Verificable con SHA256
- ✅ Compresión eficiente

### Naming Convention

```
fi-{SPRINT}-{TAG}-{DATE}.bundle
```

**Ejemplo**:
```
fi-SPR-2025W44-v0.3.0-2025-11-09.bundle
```

### SHA256 Validation

Cada bundle tiene su SHA256:

```bash
# Generar SHA256
shasum -a 256 fi-SPR-2025W44-v0.3.0-2025-11-09.bundle > SPR-2025W44-v0.3.0.sha256

# Verificar
shasum -a 256 -c SPR-2025W44-v0.3.0.sha256
```

### Retención Policy

**Regla**: Mantener **últimos 12 bundles** (6 meses de sprints)

**Automatización**:
```bash
# Sprint-close.sh aplica retención automáticamente
ls -1t "$BACKUP_DIR"/*.bundle | tail -n +13 | while read old_bundle; do
    echo "Eliminando: $old_bundle"
    rm -f "$old_bundle"
    rm -f "${old_bundle%.bundle}.sha256"
done
```

**Ubicación**: `/backups/` (dentro del repo, gitignored)

---

## 📝 Release Notes

### Auto-generación

El script `sprint-close.sh` genera automáticamente:

```markdown
# Release Notes - v0.3.0

**Sprint**: SPR-2025W44
**Fecha**: 2025-11-09
**Commits**: 47 desde v0.2.0

## Cambios

- feat(security): add LLM audit policy (a3f2d8e)
- feat(security): add LLM router policy (b4e1c9f)
- feat(export): add export manifests with SHA256 (c5d2a1e)
...

## Áreas Afectadas

backend/llm_audit_policy.py
backend/llm_router_policy.py
backend/export_policy.py
tests/test_llm_audit_policy.py
...

## Estadísticas

- Total commits: 47
- Archivos modificados: 32
```

**Ubicación**: `backups/release-notes-{TAG}.md`

### Manual Editing

**Opcional**: Editar release notes antes de tag:

```bash
# 1. Dry run (genera notas)
./scripts/sprint-close.sh SPR-2025W44 DRY_RUN

# 2. Editar notas
vim backups/release-notes-v0.3.0.md

# 3. Execute (crea tag con notas editadas)
./scripts/sprint-close.sh SPR-2025W44 EXECUTE
```

---

## 🔄 Workflow Completo

### Pre-Sprint (Día -1)

```bash
# 1. Revisar sprint anterior
git log --oneline v0.2.0..HEAD

# 2. Crear plan de sprint
cp SPRINT_TEMPLATE.md SPRINT_3_PLAN.md
vim SPRINT_3_PLAN.md

# 3. Seleccionar cards (RICE scoring)
# Ver SPRINT_ANALYSIS.md

# 4. Commit plan
git add SPRINT_3_PLAN.md
git commit -m "docs(sprint3): add sprint 3 plan"
```

### Durante Sprint (Días 1-14)

```bash
# Workflow diario:
# 1. Actualizar tracker
vim SPRINT_3_TRACKER.md

# 2. Trabajar en card
# (implementar, tests, docs)

# 3. Commit
git add .
git commit -m "feat(area): description"

# 4. Push (opcional, si trabajas remoto)
git push origin main
```

### Sprint Close (Día 15)

```bash
# 1. Verificar estado
git status
git log --oneline v0.2.0..HEAD

# 2. Tests completos
./scripts/quick_test.sh
pre-commit run --all-files

# 3. DRY RUN primero
./scripts/sprint-close.sh SPR-2025W44 DRY_RUN

# 4. Revisar notas generadas
cat backups/release-notes-v0.3.0.md

# 5. Ejecutar cierre
./scripts/sprint-close.sh SPR-2025W44 EXECUTE

# 6. Verificar tag y bundle
git tag -l
ls -lh backups/

# 7. Commit tracker final
git add SPRINT_3_TRACKER.md claude.md
git commit -m "chore(sprint3): close sprint 3"

# 8. Push tag
git push origin v0.3.0
```

### Post-Sprint (Día 16)

```bash
# Retrospective:
# 1. ¿Cumplí 4h/día?
# 2. ¿Completé las cards planificadas?
# 3. ¿Velocity mejoró o empeoró?
# 4. ¿Qué aprendí?
# 5. ¿Qué cambiar para próximo sprint?

# Documentar en:
vim SPRINT_3_PLAN.md  # Sección "Retrospective"
```

---

## 📊 Tracking Metrics

### Por Sprint

- **Cards completadas** vs planificadas
- **Horas reales** vs estimadas
- **Velocity factor** (real/estimado)
- **Tests agregados**
- **LOC agregadas**
- **Commits count**

### Ejemplo (Sprint 2 Tier 1)

```
Cards: 6/6 (100%)
Horas: 2.06h real / 18h estimado
Velocity: 0.11
Tests: +48 (135 → 183)
LOC: +2,500
Commits: 7
```

**Archivo**: `SPRINT_X_TIER_Y_SUMMARY.md`

### Dashboard (SPRINT_X_TRACKER.md)

```markdown
| Métrica | Actual | Objetivo | % |
|---------|--------|----------|---|
| Días trabajados | 15/15 | 15 | 100% |
| Horas acumuladas | 60h/60h | 60h | 100% |
| Cards completadas | 12/12 | 12 | 100% |
| Commits realizados | 45 | >15 | 300% |
```

---

## 🚨 Red Flags & Accountability

### Alertas

- ⚠️ **2 días sin commit** → Alerta amarilla
- 🔴 **3 días sin progreso** → Alerta roja
- ⚫ **5 días sin actividad** → Sprint fallido

### Protocolo de Accountability

Si fallas en compromiso de 4h/día:

1. **Documentar honestamente** en SPRINT_X_TRACKER.md
2. **Analizar causa raíz** (¿prioridad real? ¿burnout? ¿distracciones?)
3. **Decidir**:
   - Continuar con compromiso renovado
   - Reducir scope (eliminar cards)
   - Pausar sprint formalmente

**Pregunta crítica**:
> ¿Free Intelligence es realmente prioritario para mí?

**Si NO**: Pausar proyecto honestamente.
**Si SÍ**: Eliminar distracciones y continuar.

---

## 🔧 Troubleshooting

### Bundle verification failed

```bash
# Regenerar SHA256
shasum -a 256 backups/fi-SPR-2025W44-v0.3.0-2025-11-09.bundle > backups/SPR-2025W44-v0.3.0.sha256

# Verificar
shasum -a 256 -c backups/SPR-2025W44-v0.3.0.sha256
```

### Tag already exists

```bash
# Ver tag existente
git show v0.3.0

# Si es correcto, no recrear
# Si es incorrecto, eliminar y recrear:
git tag -d v0.3.0
./scripts/sprint-close.sh SPR-2025W44 EXECUTE
```

### No commits since last tag

```bash
# Verificar
git log v0.2.0..HEAD

# Si no hay commits, no crear tag nuevo
# Script detecta esto automáticamente
```

### Release notes vacías

```bash
# Problema: No hay commits desde último tag

# Solución: Asegurar que hay trabajo para tag
git log --oneline HEAD

# Si hay commits pero no desde tag:
git describe --tags --abbrev=0  # Ver último tag
git log <LAST_TAG>..HEAD        # Ver commits desde tag
```

---

## 📚 Referencias

- **Semantic Versioning**: https://semver.org/
- **Git Bundles**: https://git-scm.com/docs/git-bundle
- **Conventional Commits**: https://www.conventionalcommits.org/

---

## ✅ Checklist de Cierre de Sprint

Antes de ejecutar `sprint-close.sh EXECUTE`:

- [ ] Todos los tests pasan (`./scripts/quick_test.sh`)
- [ ] Pre-commit hooks pasan (`pre-commit run --all-files`)
- [ ] SPRINT_X_TRACKER.md actualizado con métricas finales
- [ ] Retrospective completada en SPRINT_X_PLAN.md
- [ ] Git status limpio (staged changes committeados)
- [ ] DRY_RUN ejecutado y revisado
- [ ] Release notes revisadas (opcional: editadas manualmente)
- [ ] Backups directory existe y tiene espacio
- [ ] Timezone correcto (America/Mexico_City)

Una vez ejecutado:

- [ ] Tag creado (`git tag -l`)
- [ ] Bundle generado (`ls -lh backups/`)
- [ ] SHA256 generado
- [ ] Entrada en claude.md agregada
- [ ] SPRINT_X_TRACKER.md committeado
- [ ] Tag pusheado a remoto (opcional)

---

## 🎯 Status

- **Implementación**: Completa ✅
- **Script**: sprint-close.sh (213 líneas) ✅
- **Documentación**: Completa ✅
- **Tested**: Dry run ejecutado ✅
- **Versionado**: Semántico automático ✅

**Free Intelligence ahora tiene cadencia quincenal automatizada** 🚀
