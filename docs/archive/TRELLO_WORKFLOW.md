# Trello Workflow Validation

**Última actualización**: 2025-10-28
**Versión**: 1.0.0

---

## 🎯 Objetivo

Prevenir violaciones de workflow Kanban mediante validación automática antes de mover cards.

**Regla crítica**: **NUNCA** dejar "⚙️ In Progress" vacío.

---

## 🚨 Reglas de Workflow

### Regla 1: In Progress Nunca Vacío

Cada vez que una card sale de "In Progress" (a Testing o Done):

1. ✅ **Verificar INMEDIATAMENTE** si la lista quedó vacía
2. ✅ **Mover siguiente card** prioritaria (P0 > P1 > P2) de Sprint/Backlog
3. ✅ **Documentar movimiento** en bitácora o comentario
4. ❌ **NO continuar** con otras tareas hasta restaurar workflow

### Regla 2: Prioridad de Cards

Orden de selección para mover a "In Progress":

1. **P0** (crítico) - bloquea todo lo demás
2. **P1** (high) - siguiente en importancia
3. **P2** (medium) - backlog normal

---

## 🔧 Herramientas de Validación

### 1. Script Python (Recomendado)

**Ubicación**: `scripts/trello_workflow.py`

#### Uso

```bash
# Ver estado actual del workflow
python3 scripts/trello_workflow.py status

# Validar movimiento ANTES de ejecutar
python3 scripts/trello_workflow.py validate <card_id> <target_list_id>

# Mover card con validación automática
python3 scripts/trello_workflow.py move <card_id> <target_list_id>

# Mover automáticamente siguiente card a In Progress
python3 scripts/trello_workflow.py move-next-to-progress
```

#### Ejemplos

```bash
# Ejemplo 1: Ver estado
$ python3 scripts/trello_workflow.py status

📊 TRELLO WORKFLOW STATUS
============================================================

✅ To Prioritize: 2 card(s)
✅ Sprint: 5 card(s)
✅ In Progress: 1 card(s)
✅ Testing: 3 card(s)
✅ Done: 42 card(s)

✅ Workflow is healthy

# Ejemplo 2: Validar movimiento a Testing
$ python3 scripts/trello_workflow.py validate 68fc000ef603047aa45dde8e 68fc0116783741e5e925a633

🔍 VALIDATING WORKFLOW...

📊 In Progress: 1 card(s)
   After move: 0 card(s)

⚠️  WARNING: In Progress will become empty!
📊 To Do (Sprint): 5 card(s)

⚠️  REMINDER: Move next card from Sprint to In Progress first! (5 available)

# Ejemplo 3: Mover siguiente card automáticamente
$ python3 scripts/trello_workflow.py move-next-to-progress

📋 Moving card to In Progress:
   FI-CORE-FEAT-004: Middleware HTTP para LLM

✅ Moved to In Progress:
Moved card 'FI-CORE-FEAT-004: Middleware HTTP para LLM' to list '⚙️ In Progress'

# Ejemplo 4: Mover con validación (falla si viola reglas)
$ python3 scripts/trello_workflow.py move 68fc000ef603047aa45dde8e 68fc0116783741e5e925a633

🔍 VALIDATING WORKFLOW...
❌ VIOLATION: No cards available to move to In Progress!

Move cancelled due to workflow violation
```

### 2. Script Bash (Alternativo)

**Ubicación**: `scripts/validate_trello_workflow.sh`

```bash
# Validar movimiento
./scripts/validate_trello_workflow.sh <card_id> <target_list_id>

# Exit code 0 = OK
# Exit code 1 = Violación detectada
```

---

## 📋 Trello List IDs (Free Intelligence Board)

```python
LISTS = {
    "to_prioritize": "68fc0114043ad4a639ec8fce",  # 📋 To Prioritize
    "sprint":        "68fc011510584fb24b9ef5a6",  # 📝 To Do (Sprint)
    "in_progress":   "68fc0116e8a27f8caaec894d",  # ⚙️ In Progress
    "testing":       "68fc0116783741e5e925a633",  # 🧪 Testing
    "done":          "68fc0116622f29eecd78b7d4",  # ✅ Done
}
```

---

## 🔄 Workflow Correcto

### Caso 1: Sprint Tiene Cards

```
1. Card en "In Progress" completa
2. python3 scripts/trello_workflow.py move-next-to-progress
   → Mueve siguiente P0 de Sprint a In Progress
3. Mover card actual a Testing
   → OK: In Progress nunca quedó vacío
```

### Caso 2: Sprint Vacío, To Prioritize Tiene Cards

```
1. Card en "In Progress" completa
2. STOP: Sprint vacío
3. Mover manualmente card P0 de "To Prioritize" a Sprint
4. python3 scripts/trello_workflow.py move-next-to-progress
5. Mover card actual a Testing
```

### Caso 3: TODO Vacío (Situación Crítica)

```
1. Card en "In Progress" completa
2. STOP: Sprint Y To Prioritize vacíos
3. Crear nueva card P0 o replanificar sprint
4. Agregar a Sprint
5. python3 scripts/trello_workflow.py move-next-to-progress
6. Mover card actual a Testing
```

---

## ⚠️ Escenarios de Violación

### Violación Tipo 1: In Progress Vacío

**Causa**: Mover card a Testing sin verificar estado

```
❌ MALO:
   1. FI-CORE-FEAT-003 en In Progress
   2. Mover FI-CORE-FEAT-003 → Testing
   3. In Progress queda vacío
   4. VIOLACIÓN detectada demasiado tarde

✅ BUENO:
   1. FI-CORE-FEAT-003 en In Progress
   2. python3 scripts/trello_workflow.py status
   3. Validador advierte: In Progress quedará vacío
   4. Mover FI-CORE-FEAT-004 → In Progress
   5. ENTONCES mover FI-CORE-FEAT-003 → Testing
```

### Violación Tipo 2: Sprint Vacío Ignorado

**Causa**: No verificar Sprint antes de mover

```
❌ MALO:
   1. Sprint vacío
   2. Mover única card de In Progress → Testing
   3. VIOLACIÓN: No hay reemplazo disponible

✅ BUENO:
   1. Sprint vacío
   2. Validador detecta: Sprint = 0 cards
   3. Agregar cards a Sprint desde Backlog
   4. Mover siguiente → In Progress
   5. Mover actual → Testing
```

---

## 🛡️ Integración con Claude Code

### En CLAUDE.md (Reglas Críticas)

```markdown
## ⚠️ REGLAS CRÍTICAS

- **⚠️ WORKFLOW CRÍTICO**: NUNCA dejar "⚙️ In Progress" vacío. Cada vez que una card salga de In Progress:
  1. Verificar INMEDIATAMENTE si la lista quedó vacía
  2. Si está vacía, mover siguiente card prioritaria (P0 > P1 > P2) de Sprint/Backlog
  3. Documentar movimiento en bitácora
  4. NO continuar con otras tareas hasta restaurar workflow
```

### Uso en Conversaciones

**Antes de mover card**:
```bash
# Claude Code debe ejecutar SIEMPRE antes de mover:
python3 scripts/trello_workflow.py validate <card_id> <target_list>

# Si exit code = 1 → STOP y preguntar al usuario
# Si exit code = 0 → OK, proceder con move
```

---

## 📊 Métricas de Workflow

### Comando `status` Output

```
📊 TRELLO WORKFLOW STATUS
============================================================

✅ To Prioritize: 2 card(s)   # Backlog
✅ Sprint: 5 card(s)            # Ready to work
✅ In Progress: 1 card(s)       # ⚠️ Must NEVER be 0
✅ Testing: 3 card(s)           # Awaiting QA
✅ Done: 42 card(s)             # Completed

✅ Workflow is healthy          # or ❌ VIOLATION if In Progress = 0
```

### Interpretación

- **In Progress = 0**: ❌ VIOLACIÓN - acción inmediata requerida
- **In Progress = 1**: ✅ OK - pero verificar Sprint antes de mover
- **In Progress > 1**: ✅ OK - workflow saludable
- **Sprint = 0**: ⚠️ WARNING - planificar próximas cards
- **To Prioritize = 0**: ⚠️ WARNING - backlog agotado

---

## 🔗 Referencias

- Trello Board: https://trello.com/b/iJMUbpI0/free-intelligence
- CLAUDE.md: `claude.md:50-61` (Reglas Críticas)
- Trello CLI: `~/Documents/trello-cli-python/trello`

---

## 📝 Changelog

### 2025-10-28 - v1.0.0
- ✅ Script Python validador implementado
- ✅ Script Bash alternativo implementado
- ✅ Integración con CLAUDE.md
- ✅ Documentación completa
- ✅ Validación automática pre-movimiento

---

**Free Intelligence - Workflow que respeta la dignidad del proceso** 🧠
