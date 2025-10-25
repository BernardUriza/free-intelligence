# FI-TEST-FEAT-001: E2E Testing & QA Guide

**Sprint**: SPR-2025W44 (Sprint 2)
**Priority**: P0 (Obligatorio al final del sprint)
**Effort**: 4h estimadas → ~0.28h reales
**Owner**: Bernard Uriza Orozco

---

## 📋 Contexto

Como único desarrollador del proyecto, necesitas una forma estructurada de validar que todas las features implementadas en el sprint funcionan end-to-end. Esta tarjeta crea la infraestructura de testing y documentación para QA manual o automatizado.

---

## 🎯 Objetivo

Crear un sistema de validación E2E que permita:
1. Probar todas las features del Sprint 2 de manera integrada
2. Validar flujos completos (no solo unit tests)
3. Documentar test cases para futuras regresiones
4. Proporcionar evidencia de QA para el sprint review

---

## 📦 Entregables

### 1. Postman Collection (API Testing)

**Archivo**: `tests/postman/free-intelligence-sprint2.postman_collection.json`

**Incluye**:
- Environment variables (localhost, corpus_path, owner_id)
- Requests para cada endpoint:
  - Health check / System status
  - Corpus initialization con identity
  - Append interaction (con validación append-only)
  - Append embedding
  - Get corpus stats
  - Get corpus identity
  - Verify ownership
  - Audit log queries
  - Export con policy validation

**Tests automáticos en Postman**:
```javascript
// Example test in Postman
pm.test("Corpus initialized successfully", function () {
    pm.response.to.have.status(200);
    pm.expect(pm.response.json()).to.have.property('corpus_id');
});

pm.test("Append-only policy enforced", function () {
    // Try to mutate, should fail
    pm.response.to.have.status(403);
});
```

---

### 2. E2E Test Scripts (Python)

**Archivo**: `tests/e2e/test_sprint2_integration.py`

**Test scenarios**:

```python
def test_full_workflow():
    """
    E2E test: Complete workflow from corpus init to query

    Steps:
    1. Initialize corpus with owner
    2. Verify identity created
    3. Append interaction
    4. Append embedding
    5. Query stats
    6. Verify audit log created
    7. Attempt mutation (should fail)
    8. Export with policy (should validate)
    """
    pass

def test_append_only_enforcement():
    """Test that direct mutation is blocked"""
    pass

def test_audit_trail_completeness():
    """Verify all critical operations are logged"""
    pass

def test_ownership_verification():
    """Test ownership validation flow"""
    pass

def test_llm_logging_enforcement():
    """If LLM call happens, must be logged"""
    pass
```

---

### 3. QA Manual Checklist

**Archivo**: `docs/QA_CHECKLIST_SPRINT2.md`

```markdown
# Sprint 2 QA Checklist

## ✅ Políticas y Seguridad

- [ ] **Append-only Policy**
  - [ ] Can append new interactions
  - [ ] Cannot modify existing interactions
  - [ ] Cannot delete interactions
  - [ ] Error messages are clear

- [ ] **Audit Logs**
  - [ ] All critical operations logged
  - [ ] Timestamps are correct (timezone-aware)
  - [ ] Audit queries work
  - [ ] Can filter by operation type

- [ ] **Ownership Verification**
  - [ ] Correct owner can verify
  - [ ] Wrong owner fails verification
  - [ ] Salt works correctly

- [ ] **Export Policy**
  - [ ] Export creates manifest
  - [ ] Manifest includes all metadata
  - [ ] Policy violations blocked

## ✅ Observabilidad

- [ ] **Retención 90 días**
  - [ ] Cleanup job runs
  - [ ] Old logs removed
  - [ ] Recent logs preserved

- [ ] **Boot Map**
  - [ ] System startup tracked
  - [ ] Health checks recorded
  - [ ] Query functions work

- [ ] **Event Naming**
  - [ ] All events use UPPER_SNAKE_CASE
  - [ ] Validator accepts valid events
  - [ ] Validator rejects invalid events

## ✅ DevOps

- [ ] **Pipeline Gates**
  - [ ] Pre-commit hooks run
  - [ ] Event validator integrated
  - [ ] Tests must pass before commit

- [ ] **Sprint Automation**
  - [ ] Sprint close script works
  - [ ] Release notes generated
  - [ ] Tags created correctly

## ✅ Integration

- [ ] **End-to-End Flow**
  - [ ] Init → Append → Query works
  - [ ] Events logged correctly
  - [ ] Audit trail complete
  - [ ] No errors in logs
```

---

### 4. Test Data Generator

**Archivo**: `scripts/generate_test_scenarios.py`

```python
"""
Generate realistic test data for E2E testing.

Creates:
- Multiple sessions
- Varied interactions
- Different ownership scenarios
- Edge cases (long strings, special chars, etc.)
"""

def generate_test_corpus():
    """Generate complete test corpus"""
    pass

def generate_audit_scenarios():
    """Generate audit log test cases"""
    pass

def generate_export_scenarios():
    """Generate export policy test cases"""
    pass
```

---

### 5. Validation Report Template

**Archivo**: `docs/VALIDATION_REPORT_TEMPLATE.md`

```markdown
# Sprint 2 - Validation Report

**Date**: [Date]
**Tester**: Bernard Uriza Orozco
**Environment**: Local / Staging / Production

## Test Execution Summary

| Category | Total Tests | Passed | Failed | Blocked |
|----------|-------------|--------|--------|---------|
| Unit Tests | X | X | X | X |
| Integration Tests | X | X | X | X |
| E2E Tests | X | X | X | X |
| Manual QA | X | X | X | X |

## Features Validated

### ✅ PASS: Feature Name
- [x] Acceptance criteria 1
- [x] Acceptance criteria 2
- **Evidence**: Screenshot/log reference

### ❌ FAIL: Feature Name
- [ ] Acceptance criteria that failed
- **Issue**: Description
- **Severity**: Critical / High / Medium / Low

## Bugs Found

| ID | Description | Severity | Status |
|----|-------------|----------|--------|
| BUG-001 | Description | High | Open |

## Sign-off

- [ ] All critical tests passed
- [ ] Known issues documented
- [ ] Ready for production
```

---

## 🔧 Implementación

### Fase 1: Setup (30 min)

1. Crear estructura de directorios:
```bash
tests/
  e2e/
    __init__.py
    test_sprint2_integration.py
    conftest.py
  postman/
    free-intelligence-sprint2.postman_collection.json
    environment.json
```

2. Instalar dependencias:
```bash
pip install pytest-integration requests
```

### Fase 2: Postman Collection (45 min)

1. Crear collection base
2. Agregar requests para cada feature
3. Agregar tests automáticos
4. Documentar variables de entorno

### Fase 3: E2E Scripts (1h)

1. Implementar test scenarios
2. Agregar fixtures para test data
3. Configurar pytest
4. Documentar ejecución

### Fase 4: QA Checklist (30 min)

1. Crear checklist en Markdown
2. Agregar criterios de aceptación
3. Definir evidencias requeridas

### Fase 5: Validación (1h)

1. Ejecutar todos los tests
2. Llenar validation report
3. Documentar bugs encontrados
4. Sign-off del sprint

---

## ✅ Criterios de Aceptación

### Must Have

- [ ] Postman collection con >10 requests
- [ ] Cada request tiene tests automáticos
- [ ] E2E test suite con >5 scenarios
- [ ] QA checklist completo para Sprint 2
- [ ] Validation report template
- [ ] Todos los tests documentados en README

### Should Have

- [ ] Test data generator funcional
- [ ] Screenshots de evidencia
- [ ] Video walkthrough (opcional)
- [ ] CI/CD integration para E2E tests

### Nice to Have

- [ ] Postman monitor configurado
- [ ] Performance benchmarks
- [ ] Load testing básico

---

## 📊 Definition of Done

- [ ] Postman collection importable y ejecutable
- [ ] E2E tests pasan 100%
- [ ] QA checklist completado
- [ ] Validation report generado
- [ ] Sin bugs críticos abiertos
- [ ] Documentación actualizada
- [ ] Sprint review preparado con evidencias

---

## 🚀 Uso

### Ejecutar Postman Tests

```bash
# Importar collection en Postman
# File → Import → free-intelligence-sprint2.postman_collection.json

# Configurar environment
# Variables: corpus_path, owner_id, base_url

# Run collection
# Collections → Runner → Run
```

### Ejecutar E2E Tests

```bash
# Activar venv
source venv/bin/activate

# Ejecutar tests
pytest tests/e2e/ -v --tb=short

# Con coverage
pytest tests/e2e/ --cov=backend --cov-report=html
```

### Ejecutar QA Manual

```bash
# Abrir checklist
open docs/QA_CHECKLIST_SPRINT2.md

# Marcar cada item mientras pruebas
# Documentar evidencias (screenshots, logs)
# Generar validation report
```

---

## 📝 Notas

**Testing como único dev**:
- Usar Postman para smoke tests rápidos
- E2E scripts para regresiones automatizadas
- QA manual checklist para validación final
- Validation report como evidencia de calidad

**Frecuencia**:
- Unit tests: Cada commit
- Integration tests: Cada feature completa
- E2E tests: Al final del día
- QA manual: Al final del sprint

**Herramientas**:
- Postman: API testing
- pytest: E2E automation
- Markdown checklists: QA manual
- Screenshots: Evidencia visual

---

**Status**: Planned
**Dependencies**: Todas las features del Sprint 2
**Blocker**: Ninguno (se ejecuta al final)
