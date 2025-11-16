# Task Repository Refactor Plan

**Objetivo**: Eliminar el antipatrón God Module de `task_repository.py` (1,164 líneas) y aplicar SRP (Single Responsibility Principle).

**Status**: ✅ APPROVED - Ready for implementation
**Author**: Bernard Uriza Orozco
**Date**: 2025-11-15
**Sprint**: Post-STRIDE (technical debt cleanup)

---

## 🔍 Problema Actual

### Antipatrón Identificado: **God Module**
- **1,164 líneas** en un solo archivo
- **19 funciones** con responsabilidades mezcladas
- **6 áreas de responsabilidad** diferentes (Task CRUD, Chunks, Transcription, Audio, Diarization, Compat)
- **Acoplamiento alto** con HDF5 directo en todas las funciones
- **Difícil de testear** (mocking complejo por tamaño)
- **Bugs recientes**: `segment.speaker.encode()` (línea 1077) - asumió tipo string cuando era dataclass

### Impacto en Producción
- ✅ Bug crítico en diarización (línea 1077) - **FIXED** (2025-11-15)
- ⚠️ Riesgo alto de regresiones en futuras modificaciones
- 🐌 Dificulta onboarding de nuevos devs (archivo intimidante)

---

## 🎯 Arquitectura Objetivo

### Nueva Estructura (SRP-compliant)

```
backend/storage/
├── repositories/
│   ├── __init__.py                    # Public API exports
│   ├── base_repository.py             # Base class con H5 connection handling
│   ├── task_repository.py             # Task CRUD (150 líneas)
│   ├── chunk_repository.py            # Chunk operations (200 líneas)
│   ├── transcription_repository.py    # Transcription storage (150 líneas)
│   ├── audio_repository.py            # Audio storage (120 líneas)
│   └── diarization_repository.py      # Diarization segments (100 líneas)
├── schemas/
│   ├── __init__.py
│   ├── task_schema.py                 # TaskType, task metadata schemas
│   ├── chunk_schema.py                # Chunk data schemas
│   └── h5_types.py                    # HDF5 dtype definitions
├── migrations/
│   ├── __init__.py
│   └── v1_legacy_compat.py            # Backward compatibility layer
└── task_repository.py                 # LEGACY (deprecated, kept for compat)
```

**Total estimado**: ~720 líneas distribuidas (vs 1,164 líneas monolíticas)

---

## 📦 Distribución de Responsabilidades

### 1. `base_repository.py` (80 líneas)
**Responsabilidad**: HDF5 connection management, common utilities

```python
class BaseH5Repository:
    """Base repository with H5 connection handling."""

    def __init__(self, corpus_path: str = "storage/corpus.h5"):
        self.corpus_path = corpus_path

    def _open_h5(self, mode: str = 'a'):
        """Context manager for H5 file access."""
        ...

    def _get_session_path(self, session_id: str) -> str:
        """Build session path."""
        return f"/sessions/{session_id}"

    def _get_task_path(self, session_id: str, task_type: TaskType) -> str:
        """Build task path."""
        return f"/sessions/{session_id}/tasks/{task_type.value}"
```

### 2. `task_repository.py` (NEW - 150 líneas)
**Responsabilidad**: Task CRUD operations only

**Funciones migradas**:
- `ensure_task_exists()` - Create task structure
- `task_exists()` - Check task existence
- `list_session_tasks()` - List all tasks for session
- `update_task_metadata()` - Update task metadata
- `get_task_metadata()` - Get task metadata

**Ejemplo**:
```python
class TaskRepository(BaseH5Repository):
    """Task-level CRUD operations."""

    def create_task(self, session_id: str, task_type: TaskType) -> None:
        """Create task structure in HDF5."""
        ...

    def get_metadata(self, session_id: str, task_type: TaskType) -> dict:
        """Get task metadata."""
        ...
```

### 3. `chunk_repository.py` (200 líneas)
**Responsabilidad**: Chunk-level operations

**Funciones migradas**:
- `append_chunk_to_task()` - Append chunk data
- `count_task_chunks()` - Count chunks (total, processed)
- `get_task_chunks()` - Get all chunks
- `create_empty_chunk()` - Create empty chunk
- `update_chunk_dataset()` - Update chunk datasets

**Ejemplo**:
```python
class ChunkRepository(BaseH5Repository):
    """Chunk storage and retrieval."""

    def append_chunk(
        self,
        session_id: str,
        task_type: TaskType,
        chunk_idx: int,
        datasets: dict[str, Any]
    ) -> None:
        """Append chunk with typed datasets."""
        ...

    def count_chunks(self, session_id: str, task_type: TaskType) -> tuple[int, int]:
        """Return (total, processed)."""
        ...
```

### 4. `transcription_repository.py` (150 líneas)
**Responsabilidad**: Transcription-specific storage

**Funciones migradas**:
- `get_task_transcript()` - Get full transcript
- `add_webspeech_transcripts()` - Add WebSpeech interim results
- `add_full_transcription()` - Add final full transcription

**Ejemplo**:
```python
class TranscriptionRepository(BaseH5Repository):
    """Transcription storage (3 sources: WebSpeech, Chunks, Full)."""

    def save_webspeech_transcripts(
        self,
        session_id: str,
        transcripts: list[str]
    ) -> None:
        """Save WebSpeech interim transcripts."""
        ...

    def get_full_transcript(self, session_id: str) -> str:
        """Get concatenated full transcript."""
        ...
```

### 5. `audio_repository.py` (120 líneas)
**Responsabilidad**: Audio file storage

**Funciones migradas**:
- `add_full_audio()` - Save full audio file
- `add_audio_to_chunk()` - Save chunk audio
- `get_chunk_audio_bytes()` - Retrieve chunk audio

**Ejemplo**:
```python
class AudioRepository(BaseH5Repository):
    """Audio blob storage."""

    def save_full_audio(
        self,
        session_id: str,
        audio_bytes: bytes,
        mime_type: str
    ) -> None:
        """Save full session audio."""
        ...

    def get_chunk_audio(
        self,
        session_id: str,
        task_type: TaskType,
        chunk_idx: int
    ) -> Optional[bytes]:
        """Retrieve chunk audio bytes."""
        ...
```

### 6. `diarization_repository.py` (100 líneas)
**Responsabilidad**: Diarization segments storage

**Funciones migradas**:
- `save_diarization_segments()` - **BUG FIX INCLUDED** (Speaker.speaker_id)
- `get_diarization_segments()` - Retrieve segments

**Ejemplo**:
```python
class DiarizationRepository(BaseH5Repository):
    """Diarization segment storage."""

    def save_segments(
        self,
        session_id: str,
        segments: list[DiarizationSegment]
    ) -> None:
        """Save diarization segments.

        BUG FIX (2025-11-15): segment.speaker is Speaker dataclass,
        extract speaker_id string for HDF5 storage.
        """
        for i, segment in enumerate(segments):
            seg_group.create_dataset(
                "speaker",
                data=segment.speaker.speaker_id.encode("utf-8")  # ✅ FIXED
            )
        ...
```

### 7. `migrations/v1_legacy_compat.py` (120 líneas)
**Responsabilidad**: Backward compatibility

**Funciones migradas**:
- `get_session_chunks_compat()` - Legacy API compatibility

**Ejemplo**:
```python
class LegacyTaskRepository:
    """Compatibility layer for old task_repository.py API."""

    def __init__(self):
        # Delegate to new repositories
        self.task_repo = TaskRepository()
        self.chunk_repo = ChunkRepository()
        ...

    def get_session_chunks_compat(self, session_id: str) -> list[dict]:
        """Legacy API (deprecated)."""
        warnings.warn(
            "get_session_chunks_compat is deprecated, use ChunkRepository.get_chunks()",
            DeprecationWarning
        )
        return self.chunk_repo.get_chunks(session_id, TaskType.TRANSCRIPTION)
```

---

## 🔄 Plan de Migración (Incremental)

### Fase 1: Preparación (1 día)
- [ ] Crear estructura de directorios `repositories/`, `schemas/`, `migrations/`
- [ ] Implementar `base_repository.py` con connection handling
- [ ] Definir schemas en `schemas/` (tipos, constantes HDF5)
- [ ] Setup tests: `tests/repositories/` con fixtures H5 en memoria

### Fase 2: Implementación (3 días)
- [ ] **Día 1**: `task_repository.py` (nuevo) + `chunk_repository.py`
  - Migrar funciones CRUD básicas
  - Tests unitarios (mocks H5 en memoria)
- [ ] **Día 2**: `transcription_repository.py` + `audio_repository.py`
  - Migrar funciones de transcripción y audio
  - Tests con datos reales de sesiones
- [ ] **Día 3**: `diarization_repository.py` + `v1_legacy_compat.py`
  - Migrar diarización (con bug fix incluido)
  - Implementar capa de compatibilidad

### Fase 3: Integración (2 días)
- [ ] **Día 1**: Actualizar imports en codebase
  - `from backend.storage.repositories import TaskRepository, ChunkRepository, ...`
  - Mantener `task_repository.py` legacy como alias
- [ ] **Día 2**: Testing end-to-end
  - Probar workflows completos (transcription → diarization → SOAP)
  - Verificar backward compatibility con sesiones antiguas

### Fase 4: Cleanup (1 día)
- [ ] Marcar `task_repository.py` legacy como deprecated
- [ ] Documentar nueva API en `docs/repositories/`
- [ ] Agregar deprecation warnings en legacy functions
- [ ] Commit con mensaje: `refactor(storage): Split task_repository.py God Module into SRP-compliant repositories (1164 → 720 lines)`

**Total estimado**: 7 días (1 sprint completo)

---

## ✅ Beneficios Esperados

### Mantenibilidad
- ✅ Archivos pequeños (< 200 líneas) → fácil navegación
- ✅ SRP → cambios aislados, menos conflictos en PRs
- ✅ Tests unitarios por repository → CI/CD más rápido

### Calidad de Código
- ✅ Type hints estrictos en cada repository
- ✅ Documentación clara de responsabilidades
- ✅ Menos bugs por acoplamiento

### Onboarding
- ✅ Nuevos devs entienden la arquitectura en 10 min
- ✅ Cada repository tiene 1 propósito claro
- ✅ Ejemplos y tests como documentación viva

### Performance
- 🔄 Sin cambios esperados (mismo HDF5 backend)
- ⚡ Posible optimización futura: lazy loading de repositories

---

## 🧪 Estrategia de Testing

### Unit Tests (por repository)
```python
# tests/repositories/test_task_repository.py
def test_create_task(tmp_h5_file):
    repo = TaskRepository(tmp_h5_file)
    repo.create_task("session_123", TaskType.TRANSCRIPTION)
    assert repo.task_exists("session_123", TaskType.TRANSCRIPTION)

# tests/repositories/test_diarization_repository.py
def test_save_segments_with_speaker_dataclass(tmp_h5_file):
    """Regression test for Speaker.speaker_id bug (línea 1077)."""
    repo = DiarizationRepository(tmp_h5_file)
    speaker = Speaker(speaker_id="SPEAKER_01", name="Doctor", confidence=0.9)
    segment = DiarizationSegment(speaker=speaker, text="Hola", start_time=0, end_time=1)

    repo.save_segments("session_123", [segment])

    segments = repo.get_segments("session_123")
    assert segments[0]["speaker"] == "SPEAKER_01"  # ✅ String stored correctly
```

### Integration Tests
```python
# tests/integration/test_workflow_refactored.py
def test_full_workflow_with_new_repositories():
    """Test complete workflow: upload → transcribe → diarize → SOAP."""
    task_repo = TaskRepository()
    chunk_repo = ChunkRepository()
    diarization_repo = DiarizationRepository()

    # Simulate workflow
    session_id = upload_audio_chunks()
    transcription = chunk_repo.get_chunks(session_id, TaskType.TRANSCRIPTION)

    diarization_repo.save_segments(session_id, mock_segments)
    segments = diarization_repo.get_segments(session_id)

    assert len(segments) > 0
```

---

## 🚨 Riesgos y Mitigaciones

### Riesgo 1: Romper backward compatibility
**Mitigación**: Capa de compatibilidad `v1_legacy_compat.py` mantiene API antigua funcionando con deprecation warnings.

### Riesgo 2: Bugs en migración de funciones
**Mitigación**: Tests exhaustivos + comparación de outputs (legacy vs nuevo) en sesiones reales.

### Riesgo 3: Overhead de múltiples repositories
**Mitigación**: Base class `BaseH5Repository` centraliza connection handling (sin overhead adicional).

---

## 📋 Checklist de Implementación

- [ ] Crear estructura de directorios
- [ ] Implementar `BaseH5Repository`
- [ ] Migrar `TaskRepository` (5 funciones)
- [ ] Migrar `ChunkRepository` (5 funciones)
- [ ] Migrar `TranscriptionRepository` (3 funciones)
- [ ] Migrar `AudioRepository` (3 funciones)
- [ ] Migrar `DiarizationRepository` (2 funciones) - **Bug fix incluido**
- [ ] Implementar `v1_legacy_compat.py`
- [ ] Tests unitarios (100% coverage por repository)
- [ ] Actualizar imports en codebase
- [ ] Deprecation warnings en legacy API
- [ ] Documentación en `docs/repositories/`
- [ ] Commit final con stats (líneas antes/después)

---

## 📊 Métricas de Éxito

**Antes del Refactor**:
- 1 archivo: 1,164 líneas
- 19 funciones mezcladas
- 6 responsabilidades en un solo módulo
- Difícil de testear (mocking complejo)

**Después del Refactor**:
- 7 archivos: ~720 líneas totales (38% reducción)
- 19 funciones distribuidas (promedio 3-5 funciones/archivo)
- 1 responsabilidad por archivo (SRP)
- Fácil de testear (mocks específicos por repository)

**KPI**: Reducción de tiempo de onboarding de 2 horas → 30 min (75% mejora).

---

**Status**: ✅ Plan aprobado - Ready for sprint planning
**Next Steps**: Crear Trello cards para cada fase del refactor
