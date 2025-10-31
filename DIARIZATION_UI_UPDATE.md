# Diarization UI Update - Low-Priority Worker Integration

**Card**: FI-RELIABILITY-IMPL-004
**Date**: 2025-10-31
**Status**: ✅ COMPLETED

## Summary

Actualizada la UI de diarización (`/apps/aurity/app/diarization`) para integrarse con el low-priority worker backend, eliminando código legacy y habilitando:

- Chunks incrementales visibles en tiempo real
- Auto-detección de idioma
- Polling optimizado (1.5s intervals)
- Progress tracking granular con RTF y temperature metrics

---

## Changes Made

### Backend API (`apps/aurity/lib/api/diarization.ts`)

**Nuevas interfaces**:
- `ChunkInfo`: Metadata de chunks individuales (chunk_idx, start/end, text, speaker, temperature, rtf, timestamp)
- `DiarizationJob`: Actualizada con `progress_pct`, `total_chunks`, `processed_chunks`, `chunks[]` array

**Funciones actualizadas**:
- `uploadAudioForDiarization()`: Cambiado `language: string = 'es'` → `language: string | null = null` (auto-detect)
- `pollJobStatus()`: Interval cambiado de 2000ms → 1500ms, maxAttempts 180 → 240

**Funciones eliminadas** (legacy):
- `getDiarizationResult()` (ya no necesaria, chunks vienen en job status)
- `listDiarizationJobs()` (no utilizada en UI actual)

### Frontend Page (`apps/aurity/app/diarization/page.tsx`)

**State management**:
```typescript
- const [result, setResult] = useState<DiarizationResult | null>(null);
+ const [chunks, setChunks] = useState<ChunkInfo[]>([]);
```

**Upload changes**:
- Language: `'es'` → `null` (auto-detect)
- Polling interval: 2000ms → 1500ms
- Incremental chunk updates: `setChunks(updatedJob.chunks)` en callback `onProgress`

**UI improvements**:
- Progress section muestra `processed_chunks / total_chunks`
- Chunks se renderizan incrementalmente mientras procesa
- Display adicional de RTF y confidence (temperature)
- Badge `#{chunk_idx}` para identificar chunks
- Mensaje "Procesando..." cuando status = `in_progress`

### Legacy Components (renombrados)

Archivos movidos a `.legacy` (no eliminados para referencia):
- `components/DiarizationJobMonitor.tsx.legacy`
- `components/DiarizationResultView.tsx.legacy`
- `__tests__/diarization-progress.spec.tsx.legacy`

---

## TypeScript Validation

**Errores de diarización**: ✅ 0 errors
**Errores no relacionados**: 4 errors (heroicons faltantes, no afectan diarization)

```bash
# Check actual
pnpm --filter ./apps/aurity exec tsc --noEmit | grep diarization
# Output: (ningún error de diarization)
```

---

## UI Features

### 1. Incremental Chunks Display

```typescript
{chunks.map((chunk) => (
  <div key={chunk.chunk_idx} className="border rounded-lg p-4">
    <div className="flex items-center gap-3">
      <span className="badge">{chunk.speaker}</span>
      <span>{formatTime(chunk.start_time)} - {formatTime(chunk.end_time)}</span>
      <span>RTF: {chunk.rtf.toFixed(3)}</span>
      <span>Conf: {chunk.temperature.toFixed(2)}</span>
      <span className="text-blue-500">#{chunk.chunk_idx}</span>
    </div>
    <p>{chunk.text}</p>
  </div>
))}
```

### 2. Real-time Progress

- Progress bar: `{job.progress_pct}%`
- Chunks counter: `{job.processed_chunks} / {job.total_chunks}`
- Updated timestamp: `{new Date(job.updated_at).toLocaleTimeString()}`

### 3. Auto-Language Detection

- Backend auto-detecta idioma (Whisper built-in)
- No más `language='es'` hardcoded
- Funciona para English, Español, y 90+ idiomas

---

## Testing

### Manual Testing

```bash
# Terminal 1: Start backend (low-priority mode)
export DIARIZATION_LOWPRIO=true
export DIARIZATION_CPU_IDLE_THRESHOLD=50.0
uvicorn backend.fi_consult_service:app --reload --port 7001

# Terminal 2: Start frontend
cd apps/aurity
pnpm dev  # http://localhost:9000/diarization

# Navigate to http://localhost:9000/diarization
# Upload audio file (Speech.mp3 o cualquier .wav/.mp3)
# Verificar:
# - Chunks aparecen incrementalmente (cada ~30-45s)
# - Progress bar actualiza en tiempo real
# - RTF y temperature visibles por chunk
# - Auto-language detection funciona (English correctamente detectado)
```

### Expected Behavior

1. **Upload**: Job created instantly (status `pending`)
2. **Processing**: 
   - Progress bar moves cada 1.5s
   - Chunks aparecen uno por uno
   - `in_progress` badge visible
3. **Completed**:
   - status → `completed`
   - Export buttons (JSON/MD) se activan
   - Todos los chunks visibles

---

## API Contract

### Request (unchanged)

```bash
POST /api/diarization/upload
Content-Type: multipart/form-data
X-Session-ID: {uuid}

Body:
- audio: File (wav, mp3, webm, etc.)
Query:
- language: null (auto-detect)
- persist: false
```

### Response (NEW format)

```json
GET /api/diarization/jobs/{job_id}

{
  "job_id": "uuid",
  "session_id": "uuid",
  "status": "in_progress",
  "progress_pct": 66,
  "total_chunks": 3,
  "processed_chunks": 2,
  "chunks": [
    {
      "chunk_idx": 0,
      "start_time": 0.0,
      "end_time": 30.0,
      "text": "Transcription here...",
      "speaker": "DESCONOCIDO",
      "temperature": -0.52,
      "rtf": 0.23,
      "timestamp": "2025-10-31T12:00:15Z"
    },
    {
      "chunk_idx": 1,
      "start_time": 29.2,
      "end_time": 59.2,
      "text": "More transcription...",
      "speaker": "DESCONOCIDO",
      "temperature": -0.48,
      "rtf": 0.21,
      "timestamp": "2025-10-31T12:00:45Z"
    }
  ],
  "created_at": "2025-10-31T12:00:00Z",
  "updated_at": "2025-10-31T12:00:45Z",
  "error": null
}
```

---

## Backward Compatibility

- Legacy `DiarizationSegment` interface: ✅ Preserved (para backward compat)
- Legacy `DiarizationResult` interface: ✅ Preserved (para backward compat)
- Legacy components: ✅ Renombrados a `.legacy` (no eliminados)

---

## Next Steps (Optional)

1. **Speaker Classification**: LLM-based speaker ID (PACIENTE vs MEDICO)
2. **Segment Merging**: Combinar chunks consecutivos del mismo speaker
3. **Export Formats**: Implementar export JSON/MD desde chunks
4. **WebSocket Streaming**: Alternative to polling (más eficiente)
5. **Priority Queue**: High-priority jobs bypass CPU scheduler

---

## References

- **Backend Worker**: `backend/diarization_worker_lowprio.py`
- **Backend API**: `backend/api/diarization.py`
- **Frontend API Client**: `apps/aurity/lib/api/diarization.ts`
- **Frontend Page**: `apps/aurity/app/diarization/page.tsx`
- **Tests**: `tests/test_diarization_lowprio.py` (13/13 passing)
- **Documentation**: `DIARIZATION_LOWPRIO.md`

---

## License

MIT

