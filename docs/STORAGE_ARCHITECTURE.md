# AURITY Storage Architecture - HDF5 + PostgreSQL

**Last Updated**: 2025-12-08
**Status**: Production
**Compliance**: HIPAA-ready event sourcing

---

## 📊 **Sistema Dual de Almacenamiento**

AURITY usa **dos bases de datos** con responsabilidades distintas:

| Base de Datos | Tipo | Propósito | Datos Almacenados |
|--------------|------|-----------|-------------------|
| **PostgreSQL** | Relacional | Metadatos estructurados | Pacientes, médicos, clínicas, citas |
| **HDF5** | Archivos binarios | Datos clínicos inmutables | Sesiones médicas, audio, transcripciones, SOAP |

### Por Qué Dos Databases?

**PostgreSQL** → Para datos que necesitan:
- Búsquedas rápidas (por nombre, ID, fecha)
- Relaciones entre entidades (paciente → citas → médico)
- Actualizaciones frecuentes (estado de cita, contacto)
- CRUD tradicional

**HDF5** → Para datos que necesitan:
- **Inmutabilidad** (event sourcing, HIPAA compliance)
- Append-only (nunca se modifica ni elimina)
- Integridad verificable (checksums SHA256)
- Versioning automático (audit trail)
- Eficiencia con datos binarios (audio, arrays)

---

## 🗄️ **PostgreSQL: Metadatos Estructurados**

### Ubicación
```bash
DATABASE_URL=postgresql://user:pass@host:5432/aurity_db
```

### Tablas Principales

#### `patients` - Pacientes
```sql
CREATE TABLE patients (
    patient_id UUID PRIMARY KEY,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    date_of_birth DATE,
    gender VARCHAR(10),
    email VARCHAR(255),
    phone VARCHAR(20),
    address TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

#### `providers` - Médicos
```sql
CREATE TABLE providers (
    provider_id UUID PRIMARY KEY,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    specialty VARCHAR(100),
    license_number VARCHAR(50),
    email VARCHAR(255),
    phone VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### `clinics` - Clínicas
```sql
CREATE TABLE clinics (
    clinic_id UUID PRIMARY KEY,
    name VARCHAR(200),
    address TEXT,
    phone VARCHAR(20),
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### `appointments` - Citas
```sql
CREATE TABLE appointments (
    appointment_id UUID PRIMARY KEY,
    patient_id UUID REFERENCES patients(patient_id),
    doctor_id UUID REFERENCES doctors(doctor_id),
    clinic_id UUID REFERENCES clinics(clinic_id),
    scheduled_at TIMESTAMP,
    status VARCHAR(20), -- pending, confirmed, completed, cancelled
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Cuándo Usar PostgreSQL

✅ **SÍ usar PostgreSQL para**:
- Datos demográficos de pacientes (nombre, edad, contacto)
- Catálogos (médicos, clínicas, especialidades)
- Citas y agenda
- Configuración de usuarios
- Referencias entre entidades

❌ **NO usar PostgreSQL para**:
- Audio de consultas
- Transcripciones
- Notas SOAP
- Análisis de sentimiento
- Datos que requieren audit trail inmutable

---

## 📦 **HDF5: Datos Clínicos Inmutables**

### Ubicación
```bash
storage/sessions/{session_id}.h5
```

Cada sesión médica = 1 archivo HDF5 independiente.

### Estructura del Archivo HDF5

```
session_123.h5
├─ /sessions/session_123/
│   ├─ tasks/
│   │   ├─ TRANSCRIPTION/
│   │   │   ├─ chunks/
│   │   │   │   ├─ chunk_0/
│   │   │   │   │   ├─ transcript (texto)
│   │   │   │   │   ├─ audio (bytes)
│   │   │   │   │   ├─ duration (float)
│   │   │   │   │   ├─ confidence (float)
│   │   │   │   │   └─ metadata (JSON attrs)
│   │   │   │   ├─ chunk_1/
│   │   │   │   └─ chunk_N/
│   │   │   ├─ versions/
│   │   │   │   ├─ 2025-12-08T10:30:00Z (versión inicial)
│   │   │   │   └─ 2025-12-08T10:35:00Z (corrección)
│   │   │   └─ metadata (attrs)
│   │   │
│   │   ├─ DIARIZATION/
│   │   │   ├─ chunks/
│   │   │   ├─ versions/
│   │   │   └─ metadata
│   │   │
│   │   ├─ SOAP_GENERATION/
│   │   │   ├─ versions/
│   │   │   │   ├─ 2025-12-08T11:00:00Z
│   │   │   │   └─ 2025-12-08T11:15:00Z
│   │   │   └─ metadata
│   │   │
│   │   ├─ EMOTION_ANALYSIS/
│   │   │   ├─ versions/
│   │   │   └─ metadata
│   │   │
│   │   └─ ENCRYPTION/
│   │       ├─ versions/
│   │       └─ metadata
│   │
│   ├─ audio/ (audio consolidado completo)
│   └─ metadata (attrs de la sesión)
│
└─ .sha256 (checksum de integridad)
```

### Tipos de Tareas (Tasks)

1. **TRANSCRIPTION** - Conversión audio → texto (Deepgram)
2. **DIARIZATION** - Identificación de quién habla (doctor vs paciente)
3. **SOAP_GENERATION** - Notas médicas estructuradas
4. **EMOTION_ANALYSIS** - Detección de sentimiento/emoción
5. **ENCRYPTION** - Metadatos de cifrado AES-GCM-256

### ✅ **Patrón CORRECTO: Append-Only**

```python
from datetime import UTC, datetime
import h5py
import json

def save_transcription_version(session_id: str, result: dict):
    """Guarda una nueva versión de transcripción (append-only)."""
    corpus_path = f"storage/sessions/{session_id}.h5"
    timestamp = datetime.now(UTC).isoformat()
    version_path = f"/sessions/{session_id}/tasks/TRANSCRIPTION/versions/{timestamp}"

    with h5py.File(corpus_path, "a") as f:  # "a" = append mode
        # ✅ CREAR nueva versión (no modificar existente)
        result_json = json.dumps(result, ensure_ascii=False)
        f.create_dataset(
            version_path,
            data=result_json.encode("utf-8"),
            dtype=h5py.special_dtype(vlen=bytes),
            compression="gzip",
            compression_opts=9
        )

        # ✅ ACTUALIZAR puntero a versión latest (solo metadato)
        parent = f[f"/sessions/{session_id}/tasks/TRANSCRIPTION"]
        parent.attrs["latest_version"] = timestamp
        parent.attrs["version_count"] = parent.attrs.get("version_count", 0) + 1

    logger.info(
        "transcription_versioned",
        session_id=session_id,
        version=timestamp,
        size_bytes=len(result_json)
    )
```

### ❌ **Patrones PROHIBIDOS**

```python
# ❌ VIOLACIÓN #1 - Eliminar datos (destruye audit trail)
with h5py.File(path, "r+") as f:
    del f['/sessions/123/tasks/TRANSCRIPTION']  # PROHIBIDO

# ❌ VIOLACIÓN #2 - Sobrescribir datos (pierde historial)
with h5py.File(path, "r+") as f:
    f['/sessions/123/result'] = new_data  # PROHIBIDO

# ❌ VIOLACIÓN #3 - Modificar attributes inmutables
with h5py.File(path, "r+") as f:
    f.attrs['created_at'] = 'new_date'  # PROHIBIDO
```

### 🔒 **Escritura Atómica (Atomic Writes)**

Para evitar corrupción de datos, SIEMPRE usar:

```python
import os
import hashlib

def save_session_atomic(session_id: str, audio_data: bytes):
    """Escritura atómica con verificación de integridad."""
    final_path = f"storage/sessions/{session_id}.h5"
    temp_path = f"{final_path}.part"  # Archivo temporal

    try:
        # 1. Escribir a archivo temporal
        with h5py.File(temp_path, "w", libver="latest") as f:
            f.create_dataset(
                f"/sessions/{session_id}/audio",
                data=audio_data,
                compression="gzip",
                compression_opts=9
            )

            f.attrs["session_id"] = session_id
            f.attrs["created_at"] = datetime.now(UTC).isoformat()

            # Forzar escritura a disco
            f.flush()
            os.fsync(f.fileno())  # ⚡ CRÍTICO para atomicidad

        # 2. Renombrar atómicamente (garantía POSIX)
        os.rename(temp_path, final_path)  # Operación atómica

        # 3. Calcular checksum SHA256
        with open(final_path, "rb") as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()

        # 4. Guardar checksum
        checksum_path = f"{final_path}.sha256"
        with open(checksum_path, "w") as f:
            f.write(f"{file_hash}  {session_id}.h5\n")
            os.fsync(f.fileno())

        logger.info(
            "session_saved_atomic",
            session_id=session_id,
            size_bytes=len(audio_data),
            checksum=file_hash[:16]  # Primeros 16 chars
        )

    except Exception as e:
        logger.error("atomic_write_failed", session_id=session_id, error=str(e))
        raise

    finally:
        # Limpiar archivo temporal si quedó
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass
```

### Por Qué Atomic Writes?

**Sin atomicidad** (escritura directa):
```
1. Inicio escritura → Crash del servidor ❌
2. Archivo HDF5 queda corrupto
3. Datos irrecuperables
```

**Con atomicidad** (temp + rename):
```
1. Escritura a .part → Crash del servidor ✅
2. Archivo .h5 original intacto
3. .part se elimina, sistema sigue funcionando
4. Retry automático de la operación
```

---

## 🔍 **Lectura de Datos HDF5**

### Leer Versión Más Reciente

```python
def get_latest_transcription(session_id: str) -> dict | None:
    """Obtiene la transcripción más reciente."""
    corpus_path = f"storage/sessions/{session_id}.h5"

    with h5py.File(corpus_path, "r") as f:
        task_path = f"/sessions/{session_id}/tasks/TRANSCRIPTION"

        if task_path not in f:
            return None

        task_group = f[task_path]
        latest_version = task_group.attrs.get("latest_version")

        if not latest_version:
            return None

        version_path = f"{task_path}/versions/{latest_version}"
        data = f[version_path][()]

        return json.loads(data.decode("utf-8"))
```

### Leer Historial Completo (Audit Trail)

```python
def get_transcription_history(session_id: str) -> list[dict]:
    """Obtiene todas las versiones (para auditoría)."""
    corpus_path = f"storage/sessions/{session_id}.h5"
    versions = []

    with h5py.File(corpus_path, "r") as f:
        versions_path = f"/sessions/{session_id}/tasks/TRANSCRIPTION/versions"

        if versions_path not in f:
            return []

        versions_group = f[versions_path]

        for version_timestamp in sorted(versions_group.keys()):
            data = versions_group[version_timestamp][()]
            result = json.loads(data.decode("utf-8"))
            result["_version"] = version_timestamp
            versions.append(result)

    return versions
```

---

## 🛡️ **Integridad y Seguridad**

### Checksums SHA256

Cada archivo `.h5` tiene un `.h5.sha256` asociado:

```bash
storage/sessions/
├─ session_123.h5
├─ session_123.h5.sha256  # Checksum de integridad
├─ session_456.h5
└─ session_456.h5.sha256
```

Verificación:
```python
import hashlib

def verify_session_integrity(session_id: str) -> bool:
    """Verifica que el archivo no esté corrupto."""
    h5_path = f"storage/sessions/{session_id}.h5"
    checksum_path = f"{h5_path}.sha256"

    # Leer checksum esperado
    with open(checksum_path, "r") as f:
        expected_hash = f.read().split()[0]

    # Calcular checksum actual
    with open(h5_path, "rb") as f:
        actual_hash = hashlib.sha256(f.read()).hexdigest()

    is_valid = (expected_hash == actual_hash)

    if not is_valid:
        logger.error(
            "integrity_check_failed",
            session_id=session_id,
            expected=expected_hash[:16],
            actual=actual_hash[:16]
        )

    return is_valid
```

### Encriptación (Opcional)

Para datos PHI sensibles:

```python
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

def encrypt_session(session_id: str, key: bytes) -> str:
    """Encripta archivo HDF5 con AES-256-GCM."""
    plaintext_path = f"storage/sessions/{session_id}.h5"
    encrypted_path = f"{plaintext_path}.enc"

    with open(plaintext_path, "rb") as f:
        plaintext = f.read()

    # AES-256-GCM
    iv = os.urandom(12)  # 96-bit nonce
    cipher = Cipher(
        algorithms.AES(key),
        modes.GCM(iv),
        backend=default_backend()
    )
    encryptor = cipher.encryptor()

    ciphertext = encryptor.update(plaintext) + encryptor.finalize()

    # Guardar: IV + TAG + ciphertext
    with open(encrypted_path, "wb") as f:
        f.write(iv)
        f.write(encryptor.tag)
        f.write(ciphertext)

    return encrypted_path
```

---

## 📈 **Tamaño y Performance**

### Tamaños Típicos

| Tipo de Datos | Tamaño Promedio |
|--------------|-----------------|
| Chunk de audio (30s) | ~100 KB |
| Transcripción (chunk) | ~2 KB |
| Nota SOAP completa | ~5-10 KB |
| Sesión completa (30 min) | ~5-10 MB |
| Archivo HDF5 con compresión | 60-70% del original |

### Compresión

```python
# ✅ Siempre usar compresión gzip
f.create_dataset(
    path,
    data=data,
    compression="gzip",
    compression_opts=9  # Máxima compresión (más lento pero más pequeño)
)
```

### Performance Tips

1. **Batch writes**: Agrupar múltiples chunks en una transacción
2. **Compression**: Siempre usar gzip nivel 9
3. **SWMR mode**: Single-Writer-Multiple-Reader para monitoreo en vivo
4. **Chunking**: Dividir datasets grandes en chunks de ~64 KB

---

## 🚨 **Troubleshooting**

### "File is corrupted"

```python
# Verificar integridad
verify_session_integrity(session_id)

# Si falla, intentar recuperar de backup
restore_from_backup(session_id)
```

### "Cannot write to HDF5 file"

```bash
# Verificar permisos
ls -la storage/sessions/

# Verificar espacio en disco
df -h

# Verificar locks
lsof | grep .h5
```

### "Checksum mismatch"

```python
# Posible corrupción durante escritura
# Solución: Re-ejecutar el job desde el último checkpoint válido
retry_from_checkpoint(session_id, last_valid_chunk)
```

---

## 📚 **Resumen Ejecutivo**

### ¿Se guardan bien los H5?

**SÍ**, con múltiples capas de protección:

✅ **Atomic writes** (temp + rename)
✅ **fsync()** antes de rename (flush to disk)
✅ **SHA256 checksums** para cada archivo
✅ **Append-only** (inmutabilidad HIPAA)
✅ **Versioning** automático (audit trail)
✅ **Compresión gzip** (eficiencia)
✅ **Encriptación opcional** (AES-256-GCM)

### ¿Qué base de datos usa?

**DOS bases de datos complementarias**:

1. **PostgreSQL** (metadatos estructurados)
   - Pacientes, médicos, clínicas, citas
   - Búsquedas rápidas, relaciones, CRUD

2. **HDF5** (datos clínicos inmutables)
   - Audio, transcripciones, SOAP notes
   - Event sourcing, append-only, audit trail
   - Un archivo `.h5` por sesión médica

---

**Conclusión**: El sistema de almacenamiento está diseñado para **garantizar integridad y compliance** con estándares médicos (HIPAA). Los datos nunca se pierden, nunca se modifican, y siempre son verificables.
