# Diarization Service Architecture (Refactored)

## Overview

**DiarizationService** is a **pure post-processing service** that decorates pre-transcribed segments with:
- Speaker identification (PACIENTE, MEDICO, DESCONOCIDO) using Ollama
- Text improvement (ortografía, gramática) using Ollama LLM

It does **NOT** transcribe audio. That's `TranscriptionService`'s responsibility.

## Architecture

```
TranscriptionService (frontend)
  ├─ Input: Raw audio file
  ├─ Process: Transcribe with Whisper
  ├─ Output: Segments (text, start_time, end_time) - RAW, no speaker labels
  └─ Storage: corpus.h5 / storage

        ↓ Pass segments

DiarizationService (post-processing backend)
  ├─ Input: Pre-transcribed segments (no speaker labels)
  ├─ Process:
  │  ├─ For each segment:
  │  │  ├─ Classify speaker using Ollama (context-aware)
  │  │  └─ Improve text: ortografía + gramática
  │  └─ Merge consecutive segments from same speaker
  ├─ Output: Enriched segments with speaker labels + improved text
  └─ Storage: corpus.h5 / diarization.h5
```

## File Structure

```
backend/services/diarization/
├── __init__.py           # Package initialization, exports DiarizationService
├── service.py            # Main DiarizationService class (260 lines)
├── ollama.py             # Ollama integration (classify_speaker, improve_text)
├── jobs.py               # HDF5-backed job management
├── models.py             # Dataclasses (DiarizationSegment, DiarizationResult, DiarizationJob)
└── ARCHITECTURE.md       # This file
```

## Key Classes & Functions

### `DiarizationService`

Main orchestration class. **Does NOT transcribe.**

```python
class DiarizationService:
    def diarize_segments(
        self,
        session_id: str,
        segments: list[DiarizationSegment],  # ← PRE-TRANSCRIBED
        audio_file_path: str,
        audio_file_hash: str,
        duration_sec: float,
        language: str = "es",
    ) -> DiarizationResult:
        """
        Apply speaker classification + text improvement.

        Input: Already-transcribed segments (from TranscriptionService)
        Output: Same segments with speaker labels + improved text
        """
```

**Process Flow:**
1. Accept pre-transcribed segments
2. For each segment:
   - Classify speaker (PACIENTE | MEDICO | DESCONOCIDO) via Ollama
   - Improve text (ortografía, gramática) via Ollama
3. Merge consecutive segments from same speaker
4. Return enriched segments

### `DiarizationSegment`

```python
@dataclass
class DiarizationSegment:
    start_time: float          # Seconds in audio
    end_time: float
    speaker: str               # PACIENTE | MEDICO | DESCONOCIDO (added by diarization)
    text: str                  # Raw text from Whisper
    improved_text: str | None  # After LLM improvement
    confidence: float | None   # Optional LLM confidence
```

### Ollama Functions

#### `classify_speaker(text, context_before, context_after) -> str`

Prompts Ollama to classify speaker. Returns one of:
- `PACIENTE` (patient)
- `MEDICO` (doctor)
- `DESCONOCIDO` (unknown - fallback)

Gracefully degrades if:
- Ollama unavailable → returns `DESCONOCIDO`
- LLM disabled (env var) → returns `DESCONOCIDO`
- Request times out → returns `DESCONOCIDO`

#### `improve_text(text, speaker) -> str`

Prompts Ollama to improve ortografía and gramática. Returns improved text or original if:
- Ollama unavailable
- LLM disabled
- Request fails

### Job Management

```python
# Create job
job_id = create_job(session_id, audio_path, file_size)

# Get job status
job = get_job(job_id)

# Update progress
update_job(job_id, status="in_progress", progress_percent=50)
```

## Configuration (Environment Variables)

```bash
# Ollama settings
LLM_BASE_URL=http://localhost:11434
LLM_MODEL=qwen2.5:7b-instruct-q4_0
DIARIZATION_LLM_MODEL=qwen2.5:7b-instruct-q4_0  # Override default

# LLM control
FI_ENRICHMENT=on|off                           # Master kill switch
ENABLE_LLM_CLASSIFICATION=true|false           # Speaker classification
DIARIZATION_LLM_TEMP=0.1                       # Temperature (low = deterministic)
LLM_TIMEOUT_MS=60000                           # Timeout in ms
```

## Usage Example

```python
from backend.services.diarization import DiarizationService
from backend.services.diarization.models import DiarizationSegment

# Create service
service = DiarizationService()

# Get pre-transcribed segments from somewhere (TranscriptionService, corpus.h5, etc)
segments = [
    DiarizationSegment(start_time=0.0, end_time=5.0, speaker="", text="Hola doctor"),
    DiarizationSegment(start_time=5.0, end_time=10.0, speaker="", text="¿Como está?"),
    DiarizationSegment(start_time=10.0, end_time=15.0, speaker="", text="Tengo dolor de cabeza"),
]

# Apply diarization (speaker + text improvement)
result = service.diarize_segments(
    session_id="session-123",
    segments=segments,
    audio_file_path="/path/to/audio.mp3",
    audio_file_hash="sha256:abc123...",
    duration_sec=15.0,
    language="es",
)

# Result segments now have speaker labels + improved text
for seg in result.segments:
    print(f"{seg.speaker}: {seg.improved_text or seg.text}")
    # MEDICO: Hola doctor
    # MEDICO: ¿Cómo está?
    # PACIENTE: Tengo dolor de cabeza
```

## Integration Notes

### Breaking Changes from Old V1/V2

**Old behavior (V1/V2):**
- Input: Audio file path
- Process: Transcribe + diarize in one step
- Output: Diarized segments

**New behavior (Refactored):**
- Input: Pre-transcribed segments
- Process: ONLY diarize (classify speaker + improve text)
- Output: Enriched segments

This is a **intentional architectural change** to separate concerns:
- **Transcription** = TranscriptionService (Whisper, fast, focuses on speech→text)
- **Diarization** = DiarizationService (Ollama, post-processing, focuses on speaker + quality)

### Migration Path

1. **TranscriptionService** generates segments (already done ✓)
2. **DiarizationService** consumes those segments (new ✓)
3. **API** routes need updating to:
   - Call TranscriptionService first
   - Pass segments to DiarizationService
   - Return diarized results

### API Endpoint Changes (Future)

**Old:** `POST /api/diarization/upload`
- Input: Audio file
- Output: Diarized result
- Implementation: V1 or V2 pipeline (transcribe + diarize)

**New:** `POST /api/diarization/process`
- Input: Pre-transcribed segments
- Output: Enriched diarized result
- Implementation: DiarizationService.diarize_segments()

Or keep old endpoint but decompose:
```python
@router.post("/api/diarization/upload")
async def upload(file: UploadFile):
    # Step 1: Transcribe
    transcription = transcription_service.process_transcription(...)
    segments = convert_to_segments(transcription)

    # Step 2: Diarize
    result = diarization_service.diarize_segments(segments=segments, ...)

    return result
```

## Health Check

```python
health = service.health_check()
# Returns:
{
    "status": "healthy|degraded",
    "components": {
        "ollama": {
            "available": true|false,
        }
    },
    "note": "DiarizationService requires pre-transcribed segments"
}
```

## Error Handling

- **No Ollama:** Gracefully degrades to `speaker=DESCONOCIDO`, original text (no improvement)
- **Timeout:** Returns `DESCONOCIDO` speaker, original text
- **Empty segments:** Skips gracefully, returns empty result
- **LLM disabled:** Skips classification/improvement, returns segments as-is

## Performance

- Per-segment classification: ~1-2s (Ollama inference)
- Per-segment improvement: ~1-2s (Ollama inference)
- Total for N segments: ~2-4s * N (parallel could reduce, currently sequential)

**Optimization opportunity:** Batch multiple segments per Ollama request to reduce overhead.

## Testing

See `backend/tests/test_diarization_service.py` for:
- Unit tests for speaker classification
- Integration tests with mock Ollama
- End-to-end tests with real segments

## Card References

- FI-BACKEND-FEAT-004: Diarization service implementation (original)
- FI-BACKEND-FEAT-003: Transcription service (complementary)
- Refactoring: 2025-11-05 (separated from transcription, post-processing only)

## See Also

- `backend/services/transcription/` - Speech-to-text (complementary service)
- `backend/services/soap_generation/` - SOAP extraction (another post-processor)
- `backend/api/diarization.py` - API endpoints (needs update to use new architecture)
