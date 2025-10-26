# Export Policy - Free Intelligence

**Fecha**: 2025-10-25
**Task**: FI-SEC-FEAT-004
**Sprint**: SPR-2025W44 (Sprint 2)
**Autor**: Bernard Uriza Orozco

---

## 🎯 Propósito

**TODA** exportación de datos debe tener manifest con metadata completa.

Esta política garantiza:
- **Trazabilidad**: Quién exportó qué datos, cuándo y para qué
- **Non-repudiation**: SHA256 hash de datos exportados
- **Audit trail**: Registro completo de salida de datos
- **Compliance**: Documentación de exports para auditorías
- **Data sovereignty**: Control sobre dónde van los datos

---

## 📋 Política

### Reglas Obligatorias

1. ✅ **Manifest obligatorio**: Todo export debe tener `.manifest.json`
2. ✅ **SHA256 hash**: Data hash debe matchear contenido exportado
3. ✅ **Schema estricto**: Manifest debe cumplir schema definido
4. ✅ **Audit log**: Export debe registrarse en `/audit_logs/`
5. ✅ **Metadata completa**: Timestamp, user, purpose, etc.

---

## 🔧 Manifest Schema

```json
{
  "export_id": "UUID v4 único",
  "timestamp": "ISO 8601 con timezone",
  "exported_by": "owner_hash prefix o user_id",
  "data_source": "HDF5 group exportado (e.g., /interactions/)",
  "data_hash": "SHA256 de datos exportados (64 hex chars)",
  "format": "markdown | json | hdf5 | csv | txt",
  "purpose": "personal_review | backup | migration | analysis | compliance | research",
  "retention_days": 90,  // Opcional
  "includes_pii": true,  // Default: true
  "metadata": {}  // Opcional
}
```

### Campos Requeridos

- `export_id`: UUID v4 (auto-generado)
- `timestamp`: ISO 8601 con timezone (auto-generado)
- `exported_by`: Identificador de usuario
- `data_source`: HDF5 group o path de datos
- `data_hash`: SHA256 (auto-generado)
- `format`: Uno de `ALLOWED_FORMATS`
- `purpose`: Uno de `ALLOWED_PURPOSES`

### Campos Opcionales

- `retention_days`: Días de retención del export
- `includes_pii`: Si incluye datos personales (default: true)
- `metadata`: Dict con metadata adicional

---

## 💻 Uso

### 1. Crear Export con Manifest

```python
from export_policy import create_export_manifest

# 1. Exportar datos a archivo
export_file = Path("exports/my_data.md")
export_file.write_text("# My Data\n\nInteractions...")

# 2. Crear manifest automático
manifest = create_export_manifest(
    exported_by="user_hash_prefix",
    data_source="/interactions/",
    export_filepath=export_file,
    format="markdown",
    purpose="personal_review",
    retention_days=30,
    includes_pii=True,
    metadata={"notes": "Monthly review"}
)

# 3. Guardar manifest
manifest_file = export_file.with_suffix('.manifest.json')
manifest.save(manifest_file)

print(f"Export created: {export_file}")
print(f"Manifest: {manifest_file}")
print(f"Data hash: {manifest.data_hash[:16]}...")
```

### 2. Validar Export

```python
from export_policy import load_manifest, validate_export

# Cargar manifest
manifest = load_manifest(Path("exports/my_data.manifest.json"))

# Validar export (schema + hash match)
is_valid = validate_export(
    manifest,
    Path("exports/my_data.md")
)

if is_valid:
    print("✅ Export válido")
else:
    print("❌ Export inválido")
```

### 3. CLI Usage

```bash
# Crear manifest para export existente
python3 backend/export_policy.py create \
    exports/data.md \
    /interactions/ \
    markdown \
    personal_review \
    user123

# Output:
# ✅ Manifest created: exports/data.manifest.json
#    Export ID: 550e8400-e29b-41d4-a716-446655440000
#    Data hash: 9f86d081884c7d65...
#    Format: markdown
#    Purpose: personal_review

# Validar export
python3 backend/export_policy.py validate \
    exports/data.manifest.json \
    exports/data.md

# Output:
# ✅ EXPORT VALIDATION PASSED
#    Export ID: 550e8400-e29b-41d4-a716-446655440000
#    Data hash: 9f86d081884c7d65... ✓
#    Schema: Valid ✓

# Cargar manifest
python3 backend/export_policy.py load \
    exports/data.manifest.json

# Output: JSON completo del manifest
```

---

## 📊 Ejemplo Completo

### Archivo Exportado: `exports/interactions_2025-10.md`

```markdown
# Interactions Export - October 2025

## Session session_20251025_143000

**Prompt**: Explica append-only architecture
**Response**: Append-only architecture es...
**Tokens**: 1234
```

### Manifest: `exports/interactions_2025-10.manifest.json`

```json
{
  "export_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2025-10-25T23:30:00.000000+00:00",
  "exported_by": "9f87ac3a4326090e",
  "data_source": "/interactions/",
  "data_hash": "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08",
  "format": "markdown",
  "purpose": "personal_review",
  "retention_days": 30,
  "includes_pii": true,
  "metadata": {
    "month": "2025-10",
    "total_interactions": 42,
    "notes": "Monthly review for cognitive reflection"
  }
}
```

---

## 🔒 Integración con Audit Logs

Todo export debe registrarse en `/audit_logs/`:

```python
from audit_logs import append_audit_log
from export_policy import create_export_manifest

# 1. Exportar datos
export_file = Path("exports/data.md")
export_file.write_text("...")

# 2. Crear manifest
manifest = create_export_manifest(...)
manifest.save(export_file.with_suffix('.manifest.json'))

# 3. OBLIGATORIO: Registrar en audit_logs
append_audit_log(
    corpus_path="storage/corpus.h5",
    operation="DATA_EXPORTED",
    user_id=manifest.exported_by,
    endpoint="export_interactions",
    payload=manifest.data_source,
    result=str(export_file),
    status="SUCCESS",
    metadata={
        "export_id": manifest.export_id,
        "format": manifest.format,
        "purpose": manifest.purpose,
        "data_hash": manifest.data_hash[:16] + "..."
    }
)
```

---

## 🚫 Violaciones de Política

### ❌ BAD: Export sin manifest

```python
# ❌ PROHIBIDO: Export sin manifest
export_file = Path("exports/data.md")
export_file.write_text("...")
# No manifest, no audit log → VIOLACIÓN
```

### ❌ BAD: Manifest con hash incorrecto

```python
# ❌ PROHIBIDO: Hash que no match
manifest = ExportManifest(
    data_hash="wrong_hash_here",  # ❌ No match con archivo
    ...
)
```

### ❌ BAD: Manifest con formato inválido

```python
# ❌ PROHIBIDO: Formato no permitido
manifest = ExportManifest(
    format="pdf",  # ❌ No está en ALLOWED_FORMATS
    ...
)
```

### ✅ GOOD: Export completo

```python
# ✅ CORRECTO: Export + manifest + audit log
export_file = Path("exports/data.md")
export_file.write_text("...")

# Manifest automático
manifest = create_export_manifest(
    exported_by="user123",
    data_source="/interactions/",
    export_filepath=export_file,
    format="markdown",
    purpose="personal_review"
)
manifest.save(export_file.with_suffix('.manifest.json'))

# Audit log
append_audit_log(
    operation="DATA_EXPORTED",
    user_id="user123",
    payload="/interactions/",
    result=str(export_file),
    metadata={"export_id": manifest.export_id}
)
```

---

## 🧪 Validación

### Schema Validation

```python
from export_policy import validate_manifest_schema, InvalidManifest

try:
    validate_manifest_schema(manifest)
    print("✅ Schema válido")
except InvalidManifest as e:
    print(f"❌ Schema inválido: {e}")
```

### Hash Validation

```python
from export_policy import validate_export, ExportPolicyViolation

try:
    validate_export(manifest, export_file)
    print("✅ Hash match")
except ExportPolicyViolation as e:
    print(f"❌ Hash mismatch: {e}")
```

---

## 📋 Formatos Permitidos

```python
ALLOWED_FORMATS = {
    'markdown',  # Human-readable, GitHub-compatible
    'json',      # Machine-readable, structured
    'hdf5',      # Full corpus backup
    'csv',       # Tabular data
    'txt'        # Plain text
}
```

---

## 🎯 Propósitos Permitidos

```python
ALLOWED_PURPOSES = {
    'personal_review',   # User reviewing own data
    'backup',            # Backup to external storage (NAS, USB)
    'migration',         # Moving to different system
    'analysis',          # Data analysis
    'compliance',        # Legal/compliance requirement
    'research',          # Research purposes
}
```

---

## 📈 Tests

### Cobertura

- ✅ Creación de ExportManifest
- ✅ Validación de schema (UUID, ISO 8601, formats, etc.)
- ✅ Compute file hash (SHA256)
- ✅ Hash validation (match/mismatch)
- ✅ Load/save manifests
- ✅ Auto-generation de campos (export_id, timestamp, hash)
- ✅ Optional fields (retention_days, includes_pii, metadata)

**Total**: 21 tests passing (0.004s)

```bash
# Ejecutar tests
python3 -m unittest tests.test_export_policy -v
```

---

## 🔐 Security Features

### 1. Non-Repudiation

```python
# SHA256 hash prueba que datos NO fueron modificados
manifest.data_hash = "9f86d081..."  # Stored in manifest

# Al validar:
actual_hash = compute_file_hash(export_file)
assert actual_hash == manifest.data_hash  # ✅ Data integrity
```

### 2. Audit Trail

```json
// Audit log entry
{
  "audit_id": "...",
  "operation": "DATA_EXPORTED",
  "user_id": "user123",
  "payload_hash": "sha256(...)",  // Source data
  "result_hash": "sha256(...)",   // Exported file
  "metadata": {
    "export_id": "...",
    "format": "markdown",
    "purpose": "personal_review"
  }
}
```

### 3. PII Flagging

```python
# Marcar si export contiene PII
manifest = ExportManifest(
    includes_pii=True,  # ⚠️ Datos personales
    ...
)

# Útil para compliance (GDPR, etc.)
if manifest.includes_pii:
    print("⚠️ Export contains PII - handle with care")
```

---

## 🛣️ Roadmap

### Fase 1 (Actual): Manifest Schema ✅

- ExportManifest dataclass
- Schema validation
- Hash validation
- Load/save manifests
- CLI tools
- Tests completos

### Fase 2 (Futuro): Export Automation

- Función `export_interactions()` con manifest automático
- Export templates (markdown, json, csv)
- Batch export support
- Compression support (gzip)

### Fase 3 (Futuro): Export Management

- UI para crear/validar exports
- Export history browser
- Re-validation de exports antiguos
- Automatic cleanup de exports expirados

---

## 🔗 Referencias

- **Audit Logs**: `backend/audit_logs.py` (FI-SEC-FEAT-003)
- **Append-Only Policy**: `docs/no-mutation-policy.md` (FI-DATA-FIX-001)
- **HDF5 Schema**: `backend/corpus_schema.py` (FI-DATA-FEAT-001)

---

## ✅ Status Actual

- **Implementación**: Completa ✅
- **Tests**: 21/21 passing ✅
- **Documentación**: Completa ✅
- **CLI**: create, validate, load ✅

**Próximo paso**: Implementar export automation en FI-EXPORT-FEAT-001 (Sprint futuro)

---

## 📝 Ejemplo de Workflow Completo

```bash
# 1. Exportar interacciones a markdown
python3 scripts/export_interactions.py \
    --output exports/interactions_2025-10.md \
    --format markdown \
    --month 2025-10

# 2. Crear manifest (automático o manual)
python3 backend/export_policy.py create \
    exports/interactions_2025-10.md \
    /interactions/ \
    markdown \
    personal_review \
    user_hash_prefix

# 3. Validar export
python3 backend/export_policy.py validate \
    exports/interactions_2025-10.manifest.json \
    exports/interactions_2025-10.md

# 4. Resultado:
# ✅ EXPORT VALIDATION PASSED
#    Export ID: 550e8400-e29b-41d4-a716-446655440000
#    Data hash: 9f86d081884c7d65... ✓
#    Schema: Valid ✓

# 5. El export está listo para:
# - Backup en NAS
# - Review personal
# - Migración a otro sistema
# - Análisis externo
```

**Todos los exports son auditables, verificables y trazables** ✅
