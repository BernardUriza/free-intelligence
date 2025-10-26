# Free Intelligence - Manual Testing Guide

**Fecha**: 2025-10-25
**Version**: v0.2.0-tier1-security
**Autor**: Bernard Uriza Orozco + Claude Code

---

## 🎯 Objetivo

Probar **end-to-end** todas las features implementadas en Free Intelligence.

**Duración estimada**: 10-15 minutos

---

## ✅ Pre-requisitos

```bash
# Verificar que estás en el directorio correcto
cd /Users/bernardurizaorozco/Documents/free-intelligence

# Verificar Python version (3.11+)
python3 --version

# Verificar que todos los tests pasan
python3 -m unittest discover tests/ -v
```

**Expected output**: `Ran 183 tests in X.XXXs` + `OK`

---

## 🚀 Test 1: Generar Datos de Prueba

### Objetivo
Crear interacciones de prueba en el corpus HDF5.

### Comando
```bash
python3 scripts/generate_test_data.py
```

### Expected Output
```
🚀 FREE INTELLIGENCE - TEST DATA GENERATION
============================================================

📊 Initial Corpus Stats:
   interactions_count: 0
   embeddings_count: 0
   file_size_mb: 0.XX

📝 Generating 3 test conversations...

   Session 1: session_20251024_demo_001
      ✅ Interaction 1: ¿Qué es Free Intelligence?...
      ✅ Interaction 2: ¿Cuáles son los 5 principios fundamentales?...
      ✅ Interaction 3: ¿Cómo se estructura el corpus HDF5?...

   Session 2: session_20251024_demo_002
      ✅ Interaction 1: ¿Por qué usar HDF5 en lugar de SQLite o JSON?...
      ✅ Interaction 2: Explica el flujo de una interacción desde prompt...

   Session 3: session_20251024_demo_003
      ✅ Interaction 1: ¿Qué significa 'append-only' y por qué es import...
      ✅ Interaction 2: Muestra un ejemplo de structured log...

📊 Final Corpus Stats:
   interactions_count: 7
   embeddings_count: 7
   file_size_mb: 0.XX

📈 Changes:
   Interactions added: 7
   Embeddings added: 7
   File size change: 0.XX MB

📖 Recent Interactions (last 3):
   [1] 2025-10-25T...
       Session: session_20251024_demo_003
       Prompt: Muestra un ejemplo de structured log...
       ...

✅ Test data generation completed!
```

### ✅ Success Criteria
- 7 interactions creadas
- 7 embeddings creados
- Archivo `storage/corpus.h5` existe y tiene tamaño > 0

---

## 🔐 Test 2: Validar Append-Only Policy

### Objetivo
Verificar que el sistema NO permite mutaciones de datos.

### Comando
```bash
python3 backend/append_only_policy.py
```

### Expected Output
```
🧪 Testing Append-Only Policy

Test 1: Read operation... ✅ ALLOWED
Test 2: Append operation... ✅ ALLOWED
Test 3: Mutation operation... ❌ BLOCKED (as expected)
Test 4: Context manager... ✅ PASSED
Test 5: Dataset sizes... ✅ VERIFIED

✅ All append-only policy tests passed!
```

### ✅ Success Criteria
- Read: ALLOWED
- Append: ALLOWED
- Mutation: BLOCKED

---

## 🚫 Test 3: Validar No-Mutation Policy

### Objetivo
Verificar que el código NO contiene funciones prohibidas.

### Comando
```bash
python3 backend/mutation_validator.py
```

### Expected Output
```
✅ VALIDATION PASSED
   No mutation functions detected in backend/
   Codebase complies with append-only policy
```

### ✅ Success Criteria
- Mensaje: "VALIDATION PASSED"
- 0 violaciones detectadas

---

## 🤖 Test 4: Validar LLM Audit Policy

### Objetivo
Verificar que NO hay funciones LLM sin audit logging.

### Comando
```bash
python3 backend/llm_audit_policy.py validate backend/
```

### Expected Output
```
🔍 Validating backend against LLM audit policy...

✅ LLM AUDIT VALIDATION PASSED
   No LLM functions detected
   (Backend actual no tiene LLM calls - solo infraestructura)
```

### ✅ Success Criteria
- Mensaje: "LLM AUDIT VALIDATION PASSED"
- Exit code: 0

---

## 🔀 Test 5: Validar LLM Router Policy

### Objetivo
Verificar que NO hay imports directos de APIs LLM.

### Comando
```bash
python3 backend/llm_router_policy.py validate backend/
```

### Expected Output
```
🔍 Validating backend against router policy...

✅ ROUTER POLICY VALIDATION PASSED
   No direct LLM API calls detected
   All LLM interactions must use centralized router
```

### ✅ Success Criteria
- Mensaje: "ROUTER POLICY VALIDATION PASSED"
- Exit code: 0

---

## 📦 Test 6: Crear Export con Manifest

### Objetivo
Exportar datos y crear manifest con SHA256 validation.

### Paso 1: Crear export de prueba
```bash
# Crear directorio exports si no existe
mkdir -p exports

# Crear archivo de export de prueba
echo "# Test Export\n\nThis is a test export" > exports/test_export.md
```

### Paso 2: Crear manifest
```bash
python3 backend/export_policy.py create \
    exports/test_export.md \
    /interactions/ \
    markdown \
    personal_review \
    test_user
```

### Expected Output
```
📦 Creating export manifest for exports/test_export.md...

✅ Manifest created: exports/test_export.manifest.json
   Export ID: 550e8400-e29b-41d4-a716-446655440000
   Data hash: 9f86d081884c7d65...
   Format: markdown
   Purpose: personal_review
```

### Paso 3: Validar export
```bash
python3 backend/export_policy.py validate \
    exports/test_export.manifest.json \
    exports/test_export.md
```

### Expected Output
```
🔍 Validating export...

✅ EXPORT VALIDATION PASSED
   Export ID: 550e8400-e29b-41d4-a716-446655440000
   Data hash: 9f86d081884c7d65... ✓
   Schema: Valid ✓
```

### ✅ Success Criteria
- Manifest creado: `exports/test_export.manifest.json`
- Validación pasa
- Hash match confirmado

---

## 📊 Test 7: Audit Logs

### Objetivo
Verificar que audit logs funcionan correctamente.

### Comando
```bash
python3 backend/audit_logs.py
```

### Expected Output
```
🔒 Audit Logs Demo
Initializing audit_logs group... ✅
Appending test audit log... ✅
📊 Total logs: 1
📖 Recent Audit Logs:
  [1] Operation: TEST_OPERATION
      User: demo_user
      Status: SUCCESS
```

### ✅ Success Criteria
- Audit log creado exitosamente
- Grupo /audit_logs/ inicializado
- Stats muestran count > 0

---

## 🎯 Test 8: Event Validator

### Objetivo
Verificar nomenclatura de eventos.

### Comando
```bash
python3 backend/event_validator.py list | head -20
```

### Expected Output
```
📋 Canonical Events (38 total):

CORPUS_INITIALIZED
CORPUS_ALREADY_EXISTS
CORPUS_VALIDATED
CORPUS_VALIDATION_FAILED
CORPUS_IDENTITY_ADDED
CORPUS_IDENTITY_ALREADY_EXISTS
...
```

### ✅ Success Criteria
- 38 eventos canónicos listados
- Todos en UPPER_SNAKE_CASE

---

## 🏃 Test 9: Ejecutar Todos los Tests

### Objetivo
Verificar que TODOS los tests del proyecto pasan.

### Comando
```bash
python3 -m unittest discover tests/ -v 2>&1 | tail -30
```

### Expected Output
```
...
test_validate_codebase_real (test_mutation_validator.TestMutationValidator)
Test validation of real backend directory. ... ok

----------------------------------------------------------------------
Ran 183 tests in 0.XXXs

OK
```

### ✅ Success Criteria
- **183/183 tests passing**
- Tiempo < 1 segundo
- Status: OK

---

## 🔍 Test 10: Inspeccionar Corpus HDF5

### Objetivo
Ver estructura interna del corpus.

### Comando (si tienes h5py instalado)
```bash
python3 -c "
import h5py
with h5py.File('storage/corpus.h5', 'r') as f:
    print('📁 Corpus Structure:')
    print('  Groups:', list(f.keys()))
    print('  Interactions:', f['/interactions/prompt'].shape[0])
    print('  Embeddings:', f['/embeddings/vector'].shape[0])
    print('  Metadata:')
    for key, value in f['/metadata/'].attrs.items():
        print(f'    {key}: {value}')
"
```

### Expected Output
```
📁 Corpus Structure:
  Groups: ['interactions', 'embeddings', 'metadata', 'audit_logs']
  Interactions: 7
  Embeddings: 7
  Metadata:
    created_at: 2025-10-24T...
    version: 0.1.0
    schema_version: 1
    corpus_id: 7948d081-f4eb-4674-ac98-8736f8907bec
    owner_hash: 9f87ac3a4326090e...
```

### ✅ Success Criteria
- 4 grupos: interactions, embeddings, metadata, audit_logs
- Interactions count > 0
- Metadata completo con corpus_id y owner_hash

---

## 📝 Test 11: Verificar Git Status

### Objetivo
Confirmar que todo está committeado.

### Comando
```bash
git status
```

### Expected Output
```
On branch main
Your branch is ahead of 'origin/main' by 17 commits.

Changes not staged for commit:
  (use "git add <file>..." to update what will be committed)
  (use "git restore <file>..." to discard changes in working directory)
	modified:   pyrightconfig.json

no changes added to commit (use "git add" and/or "git commit -a")
```

### ✅ Success Criteria
- Solo pyrightconfig.json pendiente (config IDE, no crítico)
- Todos los features commiteados

---

## 🏷️ Test 12: Verificar Git Tag

### Objetivo
Confirmar que el tag del release existe.

### Comando
```bash
git tag -l | grep tier1
```

### Expected Output
```
v0.2.0-tier1-security
```

### ✅ Success Criteria
- Tag `v0.2.0-tier1-security` existe

---

## 📋 Checklist Final

Marca cada test completado:

- [ ] Test 1: Generar datos de prueba ✅
- [ ] Test 2: Append-only policy ✅
- [ ] Test 3: No-mutation validator ✅
- [ ] Test 4: LLM audit policy ✅
- [ ] Test 5: LLM router policy ✅
- [ ] Test 6: Export manifest ✅
- [ ] Test 7: Audit logs ✅
- [ ] Test 8: Event validator ✅
- [ ] Test 9: Todos los tests (183) ✅
- [ ] Test 10: Inspeccionar HDF5 ✅
- [ ] Test 11: Git status ✅
- [ ] Test 12: Git tag ✅

---

## 🎉 Si Todos los Tests Pasan

**¡Felicitaciones!** Free Intelligence está funcionando correctamente con:

✅ **183 tests passing**
✅ **5 políticas enforced**
✅ **Arquitectura de 3 capas completa**
✅ **Data integrity garantizada**
✅ **Full audit trail**
✅ **Export control con SHA256**

---

## 🐛 Troubleshooting

### Error: "No module named 'h5py'"
```bash
pip3 install -r requirements.txt
```

### Error: "File not found: storage/corpus.h5"
```bash
# Inicializar corpus
python3 backend/corpus_schema.py init bernard.uriza@example.com
```

### Error: Tests failing
```bash
# Ver detalles de fallo
python3 -m unittest discover tests/ -v
```

---

## 📞 Soporte

Si encuentras algún problema:
1. Revisa los logs en `logs/` (si existen)
2. Ejecuta tests individuales para aislar el problema
3. Verifica que `config/config.yml` está correcto

---

**Happy Testing!** 🚀
