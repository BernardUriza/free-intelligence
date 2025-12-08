# CRITICAL TECHNICAL DEBT: Event Sourcing Violations

**Severity**: 🔴 CRITICAL  
**Impact**: Data integrity, audit compliance, HIPAA violations  
**Created**: 2025-12-07  
**Author**: AI Technical Auditor

## Executive Summary

El sistema AURITY declara usar **event sourcing con patrón append-only** para garantizar integridad de datos clínicos y cumplimiento HIPAA. Sin embargo, se han detectado **múltiples violaciones críticas** donde se ELIMINAN datos en lugar de versionarlos.

## Violations Detected

### 1. Audio Chunk Overwrite (`medical_chunk_handler.py:319`)

```python
# ❌ VIOLATION - Deletes existing audio data
if audio_path in f:
    del f[audio_path]  # DESTROYS AUDIT TRAIL
f.create_dataset(audio_path, data=audio_bytes)
```

**Problema**: Si un chunk se reenvía (retry por red), se pierde el audio original.

**Solución correcta**:
```python
# ✅ CORRECTO - Versioning with timestamp
audio_path = f"/sessions/{id}/tasks/TRANSCRIPTION/chunks/chunk_{N}/versions/{timestamp}/audio"
f.create_dataset(audio_path, data=audio_bytes)

# Update pointer to latest
f.attrs[f"chunk_{N}_latest_version"] = timestamp
```

### 2. Emotion Analysis Overwrite (`emotion_worker.py:352`)

```python
# ❌ VIOLATION - Deletes previous emotion analysis
result_path = f"/sessions/{session_id}/tasks/EMOTION_ANALYSIS/result"
if result_path in f:
    del f[result_path]  # DESTROYS PREVIOUS ANALYSIS
```

**Problema**: Si el análisis se ejecuta múltiples veces (re-procesamiento, debugging), se pierde el historial.

**Solución correcta**:
```python
# ✅ CORRECTO - Append with timestamp
timestamp = datetime.now(UTC).isoformat()
result_path = f"/sessions/{id}/tasks/EMOTION_ANALYSIS/results/{timestamp}"
f.create_dataset(result_path, data=result_json.encode("utf-8"))

# Mark as latest
f.attrs["emotion_analysis_latest"] = timestamp
```

### 3. WebSpeech Final Overwrite (`transcription.py:503`)

```python
# ❌ VIOLATION - Deletes previous transcription
webspeech_path = f"/sessions/{id}/tasks/TRANSCRIPTION/webspeech_final"
if webspeech_path in f:
    del f[webspeech_path]  # DESTROYS AUDIT TRAIL
```

**Problema**: Si la transcripción se regenera, no hay forma de auditar qué cambió.

**Solución correcta**:
```python
# ✅ CORRECTO - Event-sourced updates
version = int(time.time() * 1000)  # millisecond precision
path = f"/sessions/{id}/tasks/TRANSCRIPTION/webspeech_versions/{version}"
f.create_dataset(path, data=webspeech_json.encode("utf-8"))

# Update metadata
f.attrs["webspeech_current_version"] = version
f.attrs["webspeech_version_count"] = (f.attrs.get("webspeech_version_count", 0) + 1)
```

## Impact Analysis

### HIPAA Compliance Risk
- **§164.312(c)(1)**: Integrity - "mechanisms to authenticate that electronic PHI has not been altered or destroyed"
- **§164.312(c)(2)**: Mechanism to protect against improper alteration
- **VIOLACIÓN**: Borrar datos clínicos previos impide auditoría de cambios

### Data Integrity Risk
- Pérdida de historial de procesamiento
- Imposible determinar CUÁNDO cambió un valor
- No hay forma de revertir a versión anterior si hay error

### Debugging & Forensics
- Imposible reproducir bugs ("¿qué datos tenía cuando falló?")
- No se puede comparar versiones de transcripciones
- Pérdida de evidencia forense en caso de disputa médica

## Remediation Plan

### Phase 1: Stop the Bleeding (Immediate)
1. ❌ **NO implementar más deletes** en HDF5
2. ✅ Code review obligatorio para operaciones HDF5
3. ✅ Pre-commit hook que bloquee `del f[...]` en archivos que usen `CORPUS_PATH`

### Phase 2: Versioning Infrastructure (Sprint N+1)
1. Crear `VersionedDatasetWriter` utility class
2. Pattern: `{base_path}/versions/{timestamp}` + `{base_path}_latest` attr
3. Migrar los 3 casos críticos identificados

### Phase 3: Migration (Sprint N+2)
1. Script de migración para datos existentes (si es necesario)
2. Actualizar tests para verificar versionado
3. Documentación de patrón estándar

## Proposed API

```python
# backend/storage/versioned_writer.py

from datetime import UTC, datetime
import h5py
from typing import Any

class VersionedDatasetWriter:
    """Writes datasets with automatic versioning (append-only)."""
    
    def write(
        self,
        f: h5py.File,
        base_path: str,
        data: Any,
        metadata: dict | None = None
    ) -> str:
        """
        Write data with automatic versioning.
        
        Args:
            f: Open HDF5 file handle
            base_path: Base path like '/sessions/{id}/tasks/TRANSCRIPTION/result'
            data: Data to write
            metadata: Optional metadata dict
            
        Returns:
            Version path where data was written
        """
        timestamp = datetime.now(UTC).isoformat()
        version_path = f"{base_path}/versions/{timestamp}"
        
        # Append new version
        f.create_dataset(version_path, data=data)
        
        # Update metadata
        if metadata:
            for key, value in metadata.items():
                f[version_path].attrs[key] = value
        
        # Mark as latest
        parent = base_path.rsplit('/', 1)[0]
        f[parent].attrs[f"{base_path.split('/')[-1]}_latest_version"] = timestamp
        
        return version_path
    
    def read_latest(self, f: h5py.File, base_path: str) -> tuple[Any, str]:
        """Read latest version of a dataset."""
        parent = base_path.rsplit('/', 1)[0]
        key = f"{base_path.split('/')[-1]}_latest_version"
        
        if key not in f[parent].attrs:
            raise KeyError(f"No versions found for {base_path}")
        
        latest = f[parent].attrs[key]
        version_path = f"{base_path}/versions/{latest}"
        return f[version_path][()], latest
```

## Acceptance Criteria

- [ ] Pre-commit hook rechaza `del f[...]` en archivos con HDF5
- [ ] `VersionedDatasetWriter` implementado y testeado
- [ ] 3 violaciones críticas migradas a versionado
- [ ] Tests verifican que existen múltiples versiones después de writes
- [ ] Documentación actualizada con patrón estándar

## References

- `claude.md` - "Append-only en datos clínicos (HDF5)"
- `copilot-instructions.md` - "Event Sourcing - Immutability"
- HIPAA §164.312(c) - Integrity Controls

---

**Status**: 🔴 OPEN  
**Priority**: P0 - Bloquea compliance HIPAA  
**Assignee**: TBD
