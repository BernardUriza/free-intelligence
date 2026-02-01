# External Diarization Import

**Feature:** Import pre-diarized transcripts from external services
**Added:** 2026-01-27
**Status:** ✅ Production Ready

---

## Overview

Free Intelligence now supports importing speaker-separated transcripts from external diarization services, eliminating the need to re-process audio. This enables integration with best-in-class providers like Cue.ai, AssemblyAI, or manual transcription workflows.

## Use Cases

1. **Cue.ai Integration** - Text-only diarization service
2. **AssemblyAI** - High-accuracy speaker diarization
3. **Manual Transcription** - Human-labeled speaker separation
4. **Hybrid Workflows** - External AI for diarization + local SOAP generation

## Endpoint

```
POST /api/workflows/aurity/sessions/{session_id}/diarization/import
```

**Status Code:** `201 Created` (on success)

## Request Format

```json
{
  "segments": [
    {
      "start_time": 0.0,
      "end_time": 5.2,
      "speaker": {
        "speaker_id": "DOCTOR",
        "name": "Dr. García",
        "confidence": 0.95
      },
      "text": "Buenas tardes, ¿cómo se encuentra hoy?",
      "confidence": 0.92
    },
    {
      "start_time": 5.5,
      "end_time": 8.3,
      "speaker": {
        "speaker_id": "PATIENT",
        "name": null,
        "confidence": 0.88
      },
      "text": "Me duele la cabeza doctor.",
      "confidence": 0.85
    }
  ],
  "provider": "cue",
  "metadata": {
    "language": "es-MX",
    "external_job_id": "cue-12345",
    "processing_time_ms": 1234
  }
}
```

### Schema

#### `ImportDiarizationRequest`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `segments` | `List[ExternalDiarizationSegment]` | ✅ | List of speaker segments (min 1) |
| `provider` | `string` | ❌ | Provider name (default: "external") |
| `metadata` | `dict` | ❌ | Custom metadata (preserved in HDF5) |

#### `ExternalDiarizationSegment`

| Field | Type | Required | Validation | Description |
|-------|------|----------|------------|-------------|
| `start_time` | `float` | ✅ | `>= 0.0` | Segment start (seconds) |
| `end_time` | `float` | ✅ | `> 0.0` | Segment end (seconds) |
| `speaker` | `ExternalSpeaker` | ✅ | - | Speaker information |
| `text` | `string` | ✅ | `min_length=1` | Transcribed text |
| `confidence` | `float` | ❌ | `0.0-1.0` | Segment confidence (default: 0.0) |

#### `ExternalSpeaker`

| Field | Type | Required | Validation | Description |
|-------|------|----------|------------|-------------|
| `speaker_id` | `string` | ✅ | - | Speaker identifier (e.g., "DOCTOR", "SPEAKER_01") |
| `name` | `string` | ❌ | - | Speaker name (optional, e.g., "Dr. Smith") |
| `confidence` | `float` | ❌ | `0.0-1.0` | Speaker assignment confidence (default: 0.0) |

## Response Format

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "imported",
  "provider": "cue",
  "segments_imported": 2,
  "speakers_identified": 2,
  "duration_seconds": 8.3,
  "speakers": [
    {
      "speaker_id": "DOCTOR",
      "name": "Dr. García",
      "confidence": 0.95
    },
    {
      "speaker_id": "PATIENT",
      "name": null,
      "confidence": 0.88
    }
  ],
  "imported_at": "2026-01-27T15:30:45.123456+00:00",
  "message": "Successfully imported 2 segments from cue"
}
```

## Integration Examples

### Cue.ai Integration

```python
import requests

# Step 1: Get diarization from Cue.ai (pseudo-code)
cue_response = cue_client.diarize_text(transcript_text)

# Step 2: Transform to Free Intelligence format
fi_payload = {
    "segments": [
        {
            "start_time": seg.start,
            "end_time": seg.end,
            "speaker": {
                "speaker_id": seg.speaker_id,
                "name": seg.speaker_name,
                "confidence": seg.confidence
            },
            "text": seg.text,
            "confidence": seg.confidence
        }
        for seg in cue_response.segments
    ],
    "provider": "cue",
    "metadata": {
        "cue_job_id": cue_response.job_id,
        "language": cue_response.language
    }
}

# Step 3: Import to Free Intelligence
session_id = "550e8400-e29b-41d4-a716-446655440000"
response = requests.post(
    f"http://localhost:7001/api/workflows/aurity/sessions/{session_id}/diarization/import",
    json=fi_payload
)

print(f"Imported {response.json()['segments_imported']} segments")
```

### AssemblyAI Integration

```python
import assemblyai as aai

# Step 1: Diarize with AssemblyAI
transcriber = aai.Transcriber()
transcript = transcriber.transcribe(
    "path/to/audio.mp3",
    config=aai.TranscriptionConfig(speaker_labels=True)
)

# Step 2: Convert format
fi_payload = {
    "segments": [
        {
            "start_time": utterance.start / 1000,  # AssemblyAI uses ms
            "end_time": utterance.end / 1000,
            "speaker": {
                "speaker_id": utterance.speaker,
                "confidence": utterance.confidence
            },
            "text": utterance.text,
            "confidence": utterance.confidence
        }
        for utterance in transcript.utterances
    ],
    "provider": "assemblyai",
    "metadata": {"transcript_id": transcript.id}
}

# Step 3: Import
response = requests.post(...)
```

### Manual Transcription

```python
# Human transcriber labeled speakers manually
manual_transcript = {
    "segments": [
        {
            "start_time": 0.0,
            "end_time": 5.0,
            "speaker": {
                "speaker_id": "DOCTOR",
                "name": "Dr. López"
            },
            "text": "Buenos días, ¿cómo te sientes hoy?",
            "confidence": 1.0  # Manual = high confidence
        },
        {
            "start_time": 5.0,
            "end_time": 10.0,
            "speaker": {
                "speaker_id": "PATIENT",
                "name": "María Rodríguez"
            },
            "text": "Buenos días doctora, me duele la garganta.",
            "confidence": 1.0
        }
    ],
    "provider": "manual",
    "metadata": {"transcriber": "Medical Assistant"}
}

response = requests.post(...)
```

## Workflow After Import

Once diarization is imported, you can proceed with:

1. **Generate SOAP Note:**
   ```bash
   POST /api/workflows/aurity/sessions/{session_id}/soap
   ```

2. **View Segments:**
   ```bash
   GET /api/workflows/aurity/sessions/{session_id}/diarization/segments
   ```

3. **Update Segment Text:**
   ```bash
   PATCH /api/workflows/aurity/sessions/{session_id}/diarization/segments/{index}
   ```

## Error Handling

### 400 Bad Request
```json
{
  "detail": "Invalid session ID format"
}
```
**Fix:** Use valid UUID format for session_id

### 422 Validation Error
```json
{
  "detail": [
    {
      "loc": ["body", "segments"],
      "msg": "ensure this value has at least 1 items",
      "type": "value_error.list.min_items"
    }
  ]
}
```
**Fix:** Provide at least 1 segment

### 500 Internal Server Error
```json
{
  "detail": "Failed to import external diarization: <error>"
}
```
**Fix:** Check logs for HDF5 write errors or repository issues

## Performance

- **No audio processing** - instant import (< 100ms)
- **HDF5 write** - single transaction (~10-50ms)
- **Metadata indexing** - minimal overhead

**Typical latency:** < 200ms for 50 segments

## Limitations

- **No validation of speaker consistency** - API trusts external provider
- **No automatic speaker merging** - if provider uses "SPEAKER_01" and "SPEAKER_1", they're treated as separate
- **No timestamp ordering validation** - segments can overlap (provider responsibility)

## Future Enhancements

- [ ] Speaker name normalization (merge similar IDs)
- [ ] Timestamp validation (warn on overlaps/gaps)
- [ ] Confidence thresholds (reject low-confidence segments)
- [ ] Batch import (multiple sessions at once)

## Testing

Run tests:
```bash
pytest tests/api/test_import_external_diarization.py -v
```

Example script:
```bash
python examples/import_external_diarization.py
```

## See Also

- [API Documentation](http://localhost:7001/docs#/sessions/import_external_diarization)
- [Example Script](../examples/import_external_diarization.py)
- [Diarization Provider Abstraction](../providers/diarization.py)
- [HDF5 Task Repository](../repositories/task_repository.py#L378-L420)

---

**Questions?** Check logs: `tail -f /tmp/backend.log | grep EXTERNAL_DIARIZATION`
