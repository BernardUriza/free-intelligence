# Free Intelligence - Quickstart

**Version**: v0.2.0-tier1-security
**Última actualización**: 2025-10-25

---

## 🚀 Inicio Rápido (3 comandos)

```bash
# 1. Ejecutar quick test (todo en uno)
./scripts/quick_test.sh

# 2. Ver datos generados
python3 backend/corpus_ops.py

# 3. Ejecutar tests completos
python3 -m unittest discover tests/ -v
```

---

## 📋 Qué Puedes Probar

### Opción 1: Quick Test (Recomendado - 30 segundos)
```bash
./scripts/quick_test.sh
```

Ejecuta automáticamente:
- ✅ 183 unit tests
- ✅ Genera 7 interacciones de prueba
- ✅ Valida no-mutation policy
- ✅ Valida LLM audit policy
- ✅ Valida LLM router policy
- ✅ Muestra stats del corpus

---

### Opción 2: Tests Individuales

#### Generar Datos de Prueba
```bash
python3 scripts/generate_test_data.py
```

Crea 7 interacciones sobre Free Intelligence en `storage/corpus.h5`.

#### Validar Políticas
```bash
# No-mutation policy
python3 backend/mutation_validator.py

# LLM audit policy
python3 backend/llm_audit_policy.py validate backend/

# LLM router policy
python3 backend/llm_router_policy.py validate backend/

# Append-only policy
python3 backend/append_only_policy.py
```

#### Export con Manifest
```bash
# Crear export
echo "# Test Export" > exports/test.md

# Crear manifest
python3 backend/export_policy.py create \
    exports/test.md \
    /interactions/ \
    markdown \
    personal_review \
    test_user

# Validar
python3 backend/export_policy.py validate \
    exports/test.manifest.json \
    exports/test.md
```

#### Ver Stats del Corpus
```bash
python3 -c "
from backend.corpus_ops import get_corpus_stats
import json
stats = get_corpus_stats('storage/corpus.h5')
print(json.dumps(stats, indent=2))
"
```

---

### Opción 3: Manual Testing Completo

```bash
# Ver guía detallada
cat MANUAL_TESTING_GUIDE.md

# O seguir paso a paso (12 tests, ~10 min)
```

---

## 📊 Expected Results

### Quick Test Output
```
🚀 FREE INTELLIGENCE - QUICK TEST
==================================

📝 Test 1/6: Running unit tests...
Ran 183 tests in 0.XXXs
OK

📝 Test 2/6: Generating test data...
   Interactions added: 7
   Embeddings added: 7

📝 Test 3/6: Validating no-mutation policy...
✅ VALIDATION PASSED

📝 Test 4/6: Validating LLM audit policy...
✅ LLM AUDIT VALIDATION PASSED

📝 Test 5/6: Validating LLM router policy...
✅ ROUTER POLICY VALIDATION PASSED

📝 Test 6/6: Checking corpus stats...
   Interactions: 7
   Embeddings: 7
   File size: 0.XX MB

==================================
✅ All quick tests completed!
```

---

## 🏗️ Arquitectura Probada

Cuando ejecutas los tests, estás verificando:

### Layer 1: Data Integrity
- ✅ Append-only HDF5 (no mutations allowed)
- ✅ No-mutation validator (AST-based)
- ✅ Corpus identity (corpus_id + owner_hash)

### Layer 2: Audit Trail
- ✅ Audit logs (/audit_logs/ group)
- ✅ LLM audit policy (all LLM calls must log)
- ✅ Export manifests (SHA256 validation)

### Layer 3: Enforcement
- ✅ LLM router policy (no direct API calls)
- ✅ Event naming (UPPER_SNAKE_CASE)
- ✅ AST validators (static analysis)

---

## 📁 Archivos Generados

Después de ejecutar los tests, tendrás:

```
storage/
  └─ corpus.h5                    # HDF5 con 7 interacciones

exports/                          # Si creaste exports
  ├─ test.md                      # Export de prueba
  └─ test.manifest.json           # Manifest con SHA256

logs/                             # Logs estructurados (si existen)
```

---

## 🐛 Troubleshooting

### Error: "Permission denied: ./scripts/quick_test.sh"
```bash
chmod +x scripts/quick_test.sh
```

### Error: "No module named 'h5py'"
```bash
pip3 install -r requirements.txt
```

### Error: "File not found: storage/corpus.h5"
```bash
# Inicializar corpus
python3 backend/corpus_schema.py init bernard.uriza@example.com
```

---

## 📚 Documentación Completa

- **Manual Testing**: `MANUAL_TESTING_GUIDE.md` (12 tests detallados)
- **Sprint Summary**: `SPRINT_2_TIER_1_SUMMARY.md`
- **Sprint Plan**: `SPRINT_2_PLAN.md`
- **Políticas**:
  - `docs/llm-audit-policy.md`
  - `docs/llm-router-policy.md`
  - `docs/export-policy.md`
  - `docs/no-mutation-policy.md`

---

## 🎯 Próximos Pasos

1. **Ejecutar quick test**: `./scripts/quick_test.sh`
2. **Explorar corpus**: Ver datos en `storage/corpus.h5`
3. **Leer docs**: Entender las políticas implementadas
4. **Tier 2** (opcional): Pre-commit hooks, observabilidad

---

## ✅ Success Criteria

Si los tests pasan, tienes:
- ✅ **183 tests** passing
- ✅ **5 políticas** enforced
- ✅ **Arquitectura de 3 capas** completa
- ✅ **Data integrity** garantizada
- ✅ **Full audit trail**
- ✅ **Export control** con SHA256

**Free Intelligence está funcionando correctamente** 🚀

---

**¿Dudas?** Revisa `MANUAL_TESTING_GUIDE.md` o los docs en `docs/`
