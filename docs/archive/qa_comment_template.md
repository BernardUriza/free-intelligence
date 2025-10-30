# QA Comment Template — LOCK-DONE Policy

**Propósito**: Template obligatorio para mover cards a ✅ Done.

**Política**: Cards sin este formato serán revertidas automáticamente a 🧪 Testing.

---

## Template Básico

```
QA: <TASK_ID> validated 2025-MM-DD

Artefactos verificados:
- <file_path_1> (<size>, <description>) ✅
- <file_path_2> (<size>, <description>) ✅

Validación ejecutada:
```bash
<command_to_verify>
```
**Output:**
```
<exit_0_evidence>
```

DoD Checklist:
- [x] Artefacto ejecutable verificado
- [x] Tests pasan (exit 0)
- [x] Logs/instrumentación agregados
- [x] Commit descriptivo con Task ID

---

## Ejemplo 1: Backend Python Feature

```
QA: FI-CLI-FEAT-002 validated 2025-10-29

Artefactos verificados:
- backend/cli/fi_test.py (234 líneas, CLI manual inference) ✅
- tests/test_cli_inference.py (185 líneas, 9 unit tests) ✅

Validación ejecutada:
```bash
python3 -m pytest tests/test_cli_inference.py -v
```
**Output:**
```
======================== 9 passed in 0.24s ========================
exit 0
```

DoD Checklist:
- [x] Artefacto ejecutable verificado (fi_test.py + tests)
- [x] Tests pasan (9/9, exit 0)
- [x] Logs instrumentados (logger calls)
- [x] Commit: feat(cli): add manual inference channel (FI-CLI-FEAT-002)

Evidencia adicional:
- CLI ejecutable: `python3 -m backend.cli.fi_test prompt "test" --dry-run`
- JSON output estructurado validado
- Error handling probado (3 casos: adapter fail, LLM fail, corpus fail)
```

---

## Ejemplo 2: Config/Policy YAML

```
QA: FI-POLICY-STR-001 validated 2025-10-29

Artefactos verificados:
- config/fi.policy.yaml (1.70KB, sovereignty/privacy/llm budgets) ✅
- config/redaction_style.yaml (2.03KB, PII patterns) ✅
- config/decision_rules.yaml (3.14KB, triage rules) ✅
- tests/test_redaction.py (5.50KB, 12 tests) ✅
- tests/test_decision_rules.py (7.29KB, 8 tests) ✅

Validación ejecutada:
```bash
python3 -m pytest tests/test_redaction.py tests/test_decision_rules.py -v
```
**Output:**
```
======================== 20 passed in 0.20s ========================
exit 0
```

Validación YAML syntax:
```bash
python3 -c "import yaml; yaml.safe_load(open('config/fi.policy.yaml')); print('✅ OK')"
```
**Output:**
```
✅ OK
exit 0
```

DoD Checklist:
- [x] Artefactos ejecutables verificados (3 YAMLs + 2 test files)
- [x] Tests pasan (20/20, exit 0)
- [x] YAML syntax válido (parseado sin errores)
- [x] Commit: feat(policy): add sovereignty policy-as-code (FI-POLICY-STR-001)
```

---

## Ejemplo 3: Frontend React/TypeScript

```
QA: FI-UI-FEAT-201 validated 2025-11-09

Artefactos verificados:
- apps/aurity/components/sessions-list.tsx (180 líneas, tabla paginada) ✅
- apps/aurity/lib/api-client.ts (120 líneas, Sessions API fetch) ✅
- tests/e2e/sessions-list.spec.ts (80 líneas, Playwright E2E) ✅

Validación ejecutada:
```bash
pnpm exec playwright test tests/e2e/sessions-list.spec.ts
```
**Output:**
```
Running 5 tests using 1 worker
  ✓ sessions-list.spec.ts:10:1 › displays sessions table (1.2s)
  ✓ sessions-list.spec.ts:15:1 › pagination works (850ms)
  ✓ sessions-list.spec.ts:20:1 › search filters sessions (920ms)
  ✓ sessions-list.spec.ts:25:1 › clicking session navigates (780ms)
  ✓ sessions-list.spec.ts:30:1 › handles empty state (650ms)

5 passed (4.4s)
exit 0
```

Type check:
```bash
pnpm exec tsc --noEmit
```
**Output:**
```
exit 0
```

DoD Checklist:
- [x] Artefactos ejecutables verificados (component + API client + tests)
- [x] E2E tests pasan (5/5, exit 0)
- [x] Type check pasa (tsc --noEmit, exit 0)
- [x] Commit: feat(ui): add sessions list with pagination (FI-UI-FEAT-201)

Evidencia adicional:
- Screenshot: sessions-list-demo.png (adjunto)
- API integration verified: GET /api/sessions responds 200
- Accessibility: keyboard navigation tested
```

---

## Campos Obligatorios

1. **Encabezado "QA:"** con Task ID y fecha
2. **Artefactos verificados** con rutas y tamaños
3. **Comando de validación** ejecutable (copy-paste ready)
4. **Output con "exit 0"** explícito
5. **DoD Checklist** con checkboxes marcados
6. **Commit reference** con Task ID

---

## Comandos de Verificación Comunes

### Python Tests
```bash
python3 -m pytest tests/test_<feature>.py -v
python3 -m pytest tests/ -k "<pattern>" -v
```

### YAML Syntax
```bash
python3 -c "import yaml; yaml.safe_load(open('<file>.yaml')); print('✅ OK')"
```

### TypeScript Type Check
```bash
pnpm exec tsc --noEmit
```

### Playwright E2E
```bash
pnpm exec playwright test tests/e2e/<test>.spec.ts
```

### Artifact Verification
```bash
python3 tools/verify_artifact.py <TASK_ID>
```

---

## Anti-Patterns (NO ACEPTABLE)

❌ **Sin exit 0 explícito:**
```
QA: Tests passed
```

❌ **Sin comandos ejecutables:**
```
QA: Todo funciona bien
```

❌ **Sin artefactos listados:**
```
QA: Implementado correctamente
```

❌ **Sin DoD checklist:**
```
QA: Done
```

---

## Enforcement

- **Butler/Automation**: Si card se mueve a ✅ Done sin comentario "QA:", auto-revert a 🧪 Testing
- **Pre-commit hook**: Bloquea commits sin Task ID
- **Manual review**: Claude Code verifica formato antes de mover cards
- **Audit**: `trello board-audit` detecta Done sin evidencia

---

**Version**: 1.0.0
**Updated**: 2025-10-29
**Policy**: LOCK-DONE (hard requirement)
