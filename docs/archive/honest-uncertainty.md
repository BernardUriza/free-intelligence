# Honest Uncertainty - Free Intelligence

**Fecha**: 2025-10-26
**Task**: FI-UI-FIX-001
**Sprint**: SPR-2025W44 (Sprint 2)
**Autor**: Bernard Uriza Orozco

---

## 🎯 Propósito

Eliminar **predicciones de certeza falsa** del lenguaje de eventos y comunicación con el usuario.

**Principio fundamental**:
> La honestidad sobre la incertidumbre es más valiosa que la ilusión de control.

**Garantiza**:
- ✅ Comunicación honesta de limitaciones
- ✅ No pretender saber lo que no sabemos
- ✅ Transparencia sobre heurísticas vs pruebas
- ✅ Lenguaje que refleja la realidad del sistema
- ✅ Confianza genuina basada en honestidad

---

## ❌ Patrones de Falsa Certeza

### 1. "VALIDATION_PASSED" → Implica certeza absoluta

**Problema**: La validación es heurística, no una prueba matemática.

**Ejemplos problemáticos**:
```python
logger.info("CORPUS_VALIDATION_PASSED", path=corpus_path)
logger.info("LLM_AUDIT_VALIDATION_PASSED", files_scanned=len(violations))
logger.info("MUTATION_VALIDATION_PASSED", files_scanned=scanned)
```

**Por qué es falso**:
- AST parsing puede tener edge cases no cubiertos
- Validación de schema no garantiza datos correctos
- Heurísticas pueden tener falsos negativos

### 2. "VERIFIED" → Sugiere prueba absoluta

**Problema**: Verificación es comparación, no prueba formal.

**Ejemplos problemáticos**:
```python
logger.info("CORPUS_OWNERSHIP_VERIFIED", path=corpus_path)
logger.info("APPEND_ONLY_VERIFIED", operation=operation)
```

**Por qué es falso**:
- Hash match no garantiza integridad de proceso
- Ownership es hash comparison, no autenticación
- "Verified" implica audit trail completo

### 3. "SUCCESS" → Binario cuando la realidad es gradual

**Problema**: Operaciones pueden tener éxito parcial.

**Ejemplos problemáticos**:
```python
status = "SUCCESS"  # En audit logs
```

**Por qué es falso**:
- Write puede succeeder pero datos incorrectos
- Export puede ser parcial
- "Success" no captura warnings o degradación

### 4. "RETRIEVED" / "LOADED" → Implica completitud

**Problema**: Datos pueden ser parciales o desactualizados.

**Ejemplos problemáticos**:
```python
logger.info("CORPUS_STATS_RETRIEVED", **stats)
logger.info("CORPUS_IDENTITY_RETRIEVED", corpus_id=identity["corpus_id"])
```

**Por qué es falso**:
- Stats son snapshot, no ground truth
- Identity puede estar desactualizada
- "Retrieved" sugiere datos completos

---

## ✅ Patrones de Honestidad

### 1. Admitir naturaleza heurística

**Antes**:
```python
logger.info("VALIDATION_PASSED", ...)
```

**Después**:
```python
logger.info("VALIDATION_COMPLETED_NO_ISSUES_FOUND", ...)
# O simplemente:
logger.info("VALIDATION_COMPLETED", issues_found=0, ...)
```

**Diferencia**: No pretende haber probado ausencia, solo reporta no haber encontrado issues.

### 2. Ser explícito sobre método

**Antes**:
```python
logger.info("CORPUS_OWNERSHIP_VERIFIED", ...)
```

**Después**:
```python
logger.info("OWNERSHIP_HASH_MATCHED", ...)
```

**Diferencia**: Describe lo que realmente hizo (comparar hash), no la conclusión (verificación).

### 3. Reportar hechos, no interpretaciones

**Antes**:
```python
status = "SUCCESS"
```

**Después**:
```python
status = "COMPLETED"  # O "OPERATION_COMPLETED"
# Con metadata:
{
    "status": "COMPLETED",
    "warnings": [],
    "degraded": false
}
```

**Diferencia**: "Completed" es fact, "Success" es interpretación.

### 4. Admitir limitaciones

**Antes**:
```python
logger.info("CORPUS_STATS_RETRIEVED", **stats)
```

**Después**:
```python
logger.info("CORPUS_STATS_COMPUTED", timestamp=now, **stats)
# O:
logger.info("STATS_SNAPSHOT_CREATED", ...)
```

**Diferencia**: "Computed" o "Snapshot" admite que es punto en tiempo, no verdad eterna.

---

## 📋 Vocabulary Guidance

### Preferred Terms (Honest)

| Term | Meaning | Use when |
|------|---------|----------|
| **COMPLETED** | Operation finished | Process ran to end |
| **MATCHED** | Values are equal | Hash comparison |
| **COMPUTED** | Calculation done | Stats, metrics |
| **SNAPSHOT** | Point-in-time view | Current state |
| **SCANNED** | Examined items | Code analysis |
| **DETECTED** | Found pattern | AST parsing |
| **ATTEMPTED** | Tried to do X | May have failed |
| **RECORDED** | Wrote to log | Audit trail |
| **COMPARED** | Checked equality | Validation |

### Avoid (False Confidence)

| Term | Why Avoid | Replace With |
|------|-----------|--------------|
| **PASSED** | Implies test proof | COMPLETED_NO_ISSUES |
| **VERIFIED** | Suggests formal proof | HASH_MATCHED, COMPARED |
| **SUCCESS** | Binary, hides nuance | COMPLETED |
| **VALIDATED** | Implies certainty | CHECKS_COMPLETED |
| **CONFIRMED** | Suggests authority | OBSERVED, DETECTED |
| **GUARANTEED** | Absolute promise | EXPECTED, DESIGNED_FOR |
| **ENSURED** | Claims certainty | ATTEMPTED_TO_ENSURE |
| **PROVEN** | Mathematical claim | TESTED, CHECKED |

### Conditional Terms (Context-Dependent)

| Term | OK When | Avoid When |
|------|---------|------------|
| **RETRIEVED** | From persistent store | Computed/derived data |
| **LOADED** | From disk/network | Generated data |
| **SAVED** | To persistent store | Cached/temporary |
| **CREATED** | New entity | Modified existing |

---

## 🔧 Implementation Guidelines

### Event Naming Convention

**Format**: `ENTITY_ACTION_QUALIFIER`

**Examples**:
```
# Good (honest)
VALIDATION_COMPLETED_NO_ISSUES
OWNERSHIP_HASH_MATCHED
STATS_SNAPSHOT_CREATED
EXPORT_COMPLETED_WITH_WARNINGS

# Bad (false confidence)
VALIDATION_PASSED
OWNERSHIP_VERIFIED
STATS_RETRIEVED
EXPORT_SUCCESS
```

### Log Messages

**Principle**: Include method and limitations

```python
# Good (honest)
logger.info(
    "MUTATION_SCAN_COMPLETED",
    files_scanned=10,
    issues_found=0,
    method="AST_parsing",
    note="Heuristic scan, not formal proof"
)

# Bad (false confidence)
logger.info(
    "MUTATION_VALIDATION_PASSED",
    files_scanned=10
)
```

### CLI Output

**Principle**: Use qualifiers

```bash
# Good (honest)
✅ Validation completed (0 issues found via AST scan)
✅ Hash comparison matched expected value
✅ Export completed (21 interactions, 0 warnings)

# Bad (false confidence)
✅ VALIDATION PASSED
✅ OWNERSHIP VERIFIED
✅ EXPORT SUCCESS
```

### Error Messages

**Principle**: Admit what we don't know

```python
# Good (honest)
logger.error(
    "VALIDATION_INCOMPLETE",
    reason="File not found",
    note="Cannot confirm compliance without access to file"
)

# Bad (implies we know)
logger.error(
    "VALIDATION_FAILED",
    reason="File not found"
)
```

---

## 📊 Specific Event Replacements

### Validation Events

| Old (False Confidence) | New (Honest) |
|------------------------|--------------|
| CORPUS_VALIDATION_PASSED | CORPUS_SCHEMA_CHECKS_COMPLETED |
| LLM_AUDIT_VALIDATION_PASSED | LLM_AUDIT_SCAN_COMPLETED_NO_VIOLATIONS |
| MUTATION_VALIDATION_PASSED | MUTATION_SCAN_COMPLETED_NO_ISSUES |
| ROUTER_POLICY_VALIDATION_PASSED | ROUTER_POLICY_SCAN_COMPLETED |
| APPEND_ONLY_VERIFIED | APPEND_ONLY_CHECKS_COMPLETED |

### Ownership/Identity Events

| Old (False Confidence) | New (Honest) |
|------------------------|--------------|
| CORPUS_OWNERSHIP_VERIFIED | OWNERSHIP_HASH_MATCHED |
| CORPUS_IDENTITY_RETRIEVED | IDENTITY_METADATA_READ |

### Data Events

| Old (False Confidence) | New (Honest) |
|------------------------|--------------|
| CORPUS_STATS_RETRIEVED | STATS_SNAPSHOT_COMPUTED |
| EXPORT_MANIFEST_VALIDATED | MANIFEST_HASH_COMPARED |
| EXPORT_VALIDATED | EXPORT_HASH_MATCHED |

### Audit Events

| Old (False Confidence) | New (Honest) |
|------------------------|--------------|
| status="SUCCESS" | status="COMPLETED" |

---

## 🧪 Testing Honest Messaging

### Test Principles

1. **Event names reflect actual operations** (not conclusions)
2. **No absolute claims** (passed, verified, guaranteed)
3. **Include method/limitations** when non-obvious
4. **Qualifiers present** (snapshot, computed, scanned)

### Test Cases

```python
def test_honest_event_naming(self):
    """Events should not claim false confidence."""
    false_confidence_terms = [
        'PASSED', 'VERIFIED', 'SUCCESS',
        'GUARANTEED', 'PROVEN', 'CONFIRMED'
    ]

    # Scan all logger calls in backend/
    for file in glob('backend/*.py'):
        with open(file) as f:
            content = f.read()
            for term in false_confidence_terms:
                assert term not in content, \
                    f"False confidence term '{term}' found in {file}"

def test_events_include_qualifiers(self):
    """Validation events should admit heuristic nature."""
    # Events like VALIDATION_* should have qualifiers
    validation_events = extract_validation_events('backend/')

    for event in validation_events:
        assert any(q in event for q in [
            'COMPLETED', 'SCANNED', 'CHECKED',
            'NO_ISSUES', 'NO_VIOLATIONS'
        ]), f"Event {event} lacks honest qualifier"
```

---

## 🎯 Benefits

### Before (False Confidence)

```
✅ VALIDATION PASSED
✅ OWNERSHIP VERIFIED
✅ EXPORT SUCCESS
```

**Problems**:
- User assumes absolute certainty
- Hides limitations of heuristics
- Sets false expectations
- Undermines trust when issues appear

### After (Honest Uncertainty)

```
✅ Validation scan completed (0 issues found via AST)
✅ Ownership hash matched expected value
✅ Export completed (21 interactions, 0 warnings)
```

**Benefits**:
- User understands method and limitations
- Realistic expectations
- Trust based on honesty
- Easier to debug when issues occur

---

## 📝 Migration Checklist

- [ ] Update all `*_VALIDATION_PASSED` events
- [ ] Replace `*_VERIFIED` with `*_MATCHED` or `*_COMPARED`
- [ ] Change `SUCCESS` to `COMPLETED` in audit logs
- [ ] Update `*_RETRIEVED` to `*_COMPUTED` or `*_READ`
- [ ] Add qualifiers to CLI output messages
- [ ] Update event_validator.py canonical list
- [ ] Update tests to check for honest messaging
- [ ] Document new event patterns
- [ ] Update SPRINT_2_PLAN.md with completion

---

## 🔗 Related Principles

**From CLAUDE.md**:
> "Lucidez con compasión: la verdad sin violencia, la precisión sin dogma"

**From Bernard's descriptor**:
> "Rechaza el poder por obediencia y abraza el conocimiento por reciprocidad"

**Free Intelligence philosophy**:
> Honest about limitations, transparent about methods, humble about knowledge

---

## ✅ Success Criteria

Honest uncertainty is implemented when:

1. ✅ No event names contain false confidence terms (PASSED, VERIFIED, SUCCESS)
2. ✅ Validation events admit heuristic nature (SCANNED, CHECKED, NO_ISSUES_FOUND)
3. ✅ Data events include qualifiers (SNAPSHOT, COMPUTED, READ)
4. ✅ CLI output explains method ("via AST scan", "hash comparison")
5. ✅ Error messages admit what we don't know
6. ✅ Tests validate honest messaging patterns
7. ✅ Documentation explains rationale

---

## 📚 References

- **Epistemic Humility**: Admitting limits of knowledge
- **Honest Signaling**: Communication that reflects reality
- **Transparency Over Confidence**: Clarity about methods and limitations

---

**Free Intelligence: Honesto sobre la incertidumbre, transparente sobre los métodos** 🔍
