# ConversationCapture Component - Technical Documentation

**Version**: 2.0
**Last Updated**: 2025-11-12
**Location**: `apps/aurity/components/medical/ConversationCapture.tsx`

## Overview

ConversationCapture is a production-ready audio recording and transcription component integrated with the Free Intelligence (FI) backend. It provides real-time transcription, audio monitoring, and comprehensive metrics for medical consultations.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    ConversationCapture                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Recorder   │  │   Polling    │  │  Monitoring  │     │
│  │   (Dual)     │  │   System     │  │   Metrics    │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│         │                  │                  │             │
│         v                  v                  v             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  Chunked     │  │  Job Status  │  │   State      │     │
│  │  Continuous  │  │  Tracker     │  │   Manager    │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                          │
                          v
        ┌─────────────────────────────────────┐
        │     Backend (FI Public API)         │
        │  - POST /api/workflows/aurity/stream│
        │  - GET /api/workflows/aurity/jobs/  │
        │  - POST /api/workflows/aurity/end-  │
        └─────────────────────────────────────┘
```

## Features

### 1. Dual Recording System

**Problem**: WebM chunks cannot be concatenated directly due to independent EBML headers.

**Solution**: Two parallel recorders:

```typescript
// Chunked recorder (3s intervals) - for real-time transcription
const recorder = await makeRecorder(stream, callback, { timeSlice: 3000 });

// Continuous recorder (no chunks) - for full audio playback
const continuousRecorder = await makeRecorder(stream, () => {}, {});
```

**Benefits**:
- ✅ Real-time transcription (chunks sent every 3s)
- ✅ Complete audio recording (single blob)
- ✅ No concatenation issues
- ✅ Immediate playback after recording

### 2. Real-Time Transcription with Polling

**Flow**:
```
User speaks → Audio chunk captured (3s)
           → Sent to backend
           → Returns job_id
           → Poll every 500ms
           → Display transcript with animations
```

**Polling Configuration**:
- Interval: 500ms
- Timeout: 60s (120 attempts)
- States: pending → processing → completed/failed

**UI Animations**:
- Fade-in container on new chunk
- Highlight last chunk with cyan background (auto fade after 3s)
- Blinking cursor at end of text
- Smooth transitions (duration-300)

### 3. Audio Analysis in Real-Time

**Metrics Tracked**:
```typescript
- audioLevel: 0-255 (current microphone input)
- SILENCE_THRESHOLD: 5 (configurable)
- AUDIO_GAIN: 2.5x (microphone amplification)
```

**Visual Indicators**:
- 🟢 **"Hablando"** - audioLevel > threshold (green pulsing dot)
- ⚪ **"Silencio"** - audioLevel ≤ threshold (gray dot)
- Progress bar with threshold line (yellow)
- Quality indicator: 🟢 Excelente / 🟡 Buena / 🔴 Baja

**Stats Grid**:
1. **Duración** - MM:SS format
2. **Palabras transcritas** - Real-time word count
3. **Segmentos (3s)** - Number of chunks sent

### 4. Advanced Monitoring Panel (Expandable)

**Performance Metrics**:
```typescript
interface ChunkStatus {
  index: number;
  status: 'uploading' | 'pending' | 'processing' | 'completed' | 'failed';
  startTime: number;
  endTime?: number;
  latency?: number;
  transcript?: string;
  error?: string;
}
```

**Metrics Displayed**:
- ⏱️ **Latencia Promedio** - Average transcription time
- 📝 **WPM** - Words Per Minute (auto-calculated)
- ✅ **Completados** - Successful chunks / Total
- ❌ **Fallidos** - Failed chunks count

**Chunk Timeline Visualization**:
- Visual grid with color-coded status
- Colors:
  - 🔵 Blue (pulsing) = Uploading
  - 🟡 Yellow = Pending
  - 🔷 Cyan (pulsing) = Processing
  - 🟢 Green = Completed
  - 🔴 Red = Failed
- Hover tooltip: Chunk #, status, latency

**Activity Log**:
- Last 10 events with timestamps
- Examples:
  ```
  [14:32:15] 🎙️ Grabación iniciada
  [14:32:18] 📤 Enviando chunk 0 (45.3KB)
  [14:32:21] Chunk 0 transcrito en 2.8s
  [14:32:24] ❌ Chunk 3 falló: Timeout
  ```

**Backend Health Monitoring**:
- 🟢 **Healthy** - All requests successful
- 🟡 **Degraded** - Some failures detected
- 🔴 **Down** - Backend unreachable

### 5. HDF5 Data Modal

**Triggered by**: "Continuar al Siguiente Paso" button

**Modal Structure**:
```
┌─────────────────────────────────────────┐
│  📄 Datos HDF5 de la Sesión             │
│  Session ID: xxx-xxx-xxx                │
├─────────────────────────────────────────┤
│  Summary Cards (4):                      │
│  - Duración Total                        │
│  - Palabras                              │
│  - WPM                                   │
│  - Chunks                                │
├─────────────────────────────────────────┤
│  Transcripción Completa (scrollable)    │
├─────────────────────────────────────────┤
│  Desglose por Chunks:                    │
│  ┌─────────────────────────────────┐    │
│  │ Chunk 0 | 2.5s | completed      │    │
│  │ "ok entonces esto debería..."   │    │
│  └─────────────────────────────────┘    │
│  ┌─────────────────────────────────┐    │
│  │ Chunk 1 | 3.1s | completed      │    │
│  │ "de aparecer el texto en..."    │    │
│  └─────────────────────────────────┘    │
├─────────────────────────────────────────┤
│  Metadatos:                              │
│  - Latencia Promedio: 2.8s              │
│  - Audio Completo: ✅ Disponible        │
├─────────────────────────────────────────┤
│  [Cerrar]      [Continuar → ]           │
└─────────────────────────────────────────┘
```

**Data Source**:
1. Tries: `GET /api/workflows/aurity/sessions/{session_id}/inspect`
2. Fallback: Uses local state (chunkStatuses, transcriptionData, etc.)

### 6. Demo Audio Playback

**Feature**: Pre-recorded medical consultation for testing

**Audio File**: `backend/static/consulta_demo.mp3` (61s)
- Doctor (male voice - onyx)
- Patient (female voice - nova)
- Generated with Azure OpenAI TTS
- Spanish (es-MX) with 0.95 speed for clarity

**Button States**:
- 🟣 Purple = Stopped/Ready
- 🟣 Purple (playing) = Playing
- 🟠 Amber = Paused

**Behavior**:
- Click 1: Play demo
- Click 2: Pause
- Click 3: Resume
- Can record while demo plays (for testing transcription)

## State Management

### Core State Variables

```typescript
// Recording state
const [isRecording, setIsRecording] = useState(false);
const [recordingTime, setRecordingTime] = useState(0);
const [transcriptionData, setTranscriptionData] = useState({ text: '' });
const [lastChunkText, setLastChunkText] = useState('');

// Audio state
const [audioLevel, setAudioLevel] = useState(0);
const [fullAudioUrl, setFullAudioUrl] = useState<string | null>(null);

// Demo state
const [isDemoPlaying, setIsDemoPlaying] = useState(false);
const [isDemoPaused, setIsDemoPaused] = useState(false);

// Monitoring state
const [chunkStatuses, setChunkStatuses] = useState<ChunkStatus[]>([]);
const [avgLatency, setAvgLatency] = useState(0);
const [wpm, setWpm] = useState(0);
const [backendHealth, setBackendHealth] = useState<'healthy' | 'degraded' | 'down'>('healthy');
const [activityLogs, setActivityLogs] = useState<string[]>([]);

// Modal state
const [showH5Modal, setShowH5Modal] = useState(false);
const [h5Data, setH5Data] = useState<any>(null);
const [showAdvancedMetrics, setShowAdvancedMetrics] = useState(false);

// Refs (don't trigger re-renders)
const sessionIdRef = useRef<string>('');
const chunkNumberRef = useRef<number>(0);
const streamingTranscriptRef = useRef<string>('');
const continuousRecorderRef = useRef<any>(null);
const fullAudioUrlRef = useRef<string | null>(null);
```

## Data Flow

### Recording Start
```
User clicks "Grabar"
  → handleStartRecording()
  → navigator.mediaDevices.getUserMedia()
  → Create 2 recorders (chunked + continuous)
  → Start audio level monitoring
  → Start timer (1s interval)
  → Set isRecording = true
```

### Chunk Processing
```
Every 3 seconds:
  → Chunked recorder fires callback
  → Check silence (skip if audioLevel < threshold)
  → Create FormData with audio blob
  → POST /api/workflows/aurity/stream
  → Receive job_id or direct transcription
  → If job_id: Start polling
  → Update chunkStatuses to 'uploading'
  → Add activity log entry
```

### Polling Cycle
```
pollJobStatus(job_id, chunk_index)
  → Set status to 'pending'
  → Loop: GET /api/workflows/aurity/jobs/{job_id} every 500ms
  → Update status based on response:
    - 'processing' → Update UI
    - 'completed' → Extract transcript, calculate latency
    - 'failed' → Log error, update health
  → On completed:
    - Append to streamingTranscriptRef
    - Update transcriptionData
    - Set lastChunkText (for animation)
    - Calculate avg latency
    - Update backendHealth to 'healthy'
```

### Recording Stop
```
User clicks "Detener"
  → handleStopRecording()
  → Stop continuous recorder → Get fullBlob
  → Create blob URL → Set fullAudioUrl
  → Stop chunked recorder
  → Stop media tracks
  → Set isRecording = false
  → Send fullBlob to backend (/end-session)
  → Backend saves and returns audio_path
  → Update fullAudioUrl with backend URL
```

### WPM Calculation
```typescript
useEffect(() => {
  if (isRecording && recordingTime > 0 && transcriptionData?.text) {
    const words = transcriptionData.text.trim().split(/\s+/).filter(w => w.length > 0).length;
    const minutes = recordingTime / 60;
    const wpm = minutes > 0 ? Math.round(words / minutes) : 0;
    setWpm(wpm);
  }
}, [isRecording, recordingTime, transcriptionData]);
```

## Backend Integration

### Endpoints Used

**1. Stream Chunk (Public Orchestrator)**
```
POST /api/workflows/aurity/stream
Content-Type: multipart/form-data

Fields:
- session_id: UUID
- chunk_number: int
- audio: Blob
- mime: string
- timestamp_start: float
- timestamp_end: float

Response:
- Direct path: { status: 'completed', transcription: string }
- Worker path: { status: 'pending', job_id: string }
```

**2. Job Status**
```
GET /api/workflows/aurity/jobs/{job_id}

Response:
{
  job_id: string,
  session_id: string,
  chunk_number: int,
  status: 'pending' | 'processing' | 'completed' | 'failed',
  transcript?: string,
  duration: float,
  language: string,
  latency_ms: int,
  error?: string
}
```

**3. End Session (Save Full Audio)**
```
POST /api/workflows/aurity/end-session
Content-Type: multipart/form-data

Fields:
- session_id: UUID
- full_audio: Blob (WebM/WAV/MP3)

Response:
{
  success: bool,
  session_id: string,
  audio_path: string,  // e.g., "/api/workflows/aurity/sessions/{id}/audio"
  chunks_count: int,
  duration: float
}
```

**4. Get Session Audio**
```
GET /api/workflows/aurity/sessions/{session_id}/audio

Response: Audio file (WebM/WAV/MP3)
```

**5. Session Inspect (Optional)**
```
GET /api/workflows/aurity/sessions/{session_id}/inspect

Response:
{
  session_id: string,
  chunks: Array<{
    index: int,
    transcript: string,
    latency_ms: int,
    status: string
  }>,
  transcription_full: string,
  word_count: int,
  duration_seconds: int,
  avg_latency_ms: float,
  wpm: int,
  full_audio_available: bool
}
```

## Configuration

### Audio Settings
```typescript
const SILENCE_THRESHOLD = 5;        // 0-255 scale (skip chunks below this)
const AUDIO_GAIN = 2.5;              // Microphone amplification
const CHUNK_INTERVAL = 3000;         // 3 seconds per chunk
const SAMPLE_RATE = 16000;           // 16kHz audio
const CHANNELS = 1;                  // Mono
```

### Polling Settings
```typescript
const POLL_INTERVAL = 500;           // 500ms between requests
const MAX_POLL_ATTEMPTS = 120;       // 60s timeout (120 * 500ms)
```

### Animation Settings
```typescript
const HIGHLIGHT_DURATION = 3000;     // Highlight new chunks for 3s
const FADE_IN_DURATION = 300;        // Fade-in animation (ms)
const CURSOR_BLINK_RATE = 1000;      // 1s blink cycle
```

## Performance Considerations

### Optimizations

1. **Silence Skipping**
   - Saves backend processing time
   - Reduces unnecessary API calls
   - Improves latency metrics

2. **Parallel Recording**
   - No chunking overhead for full audio
   - Clean single blob for playback
   - Faster upload (single file vs concatenation)

3. **Optimistic UI**
   - Immediate blob URL for playback
   - Background upload to backend
   - Seamless transition to persistent URL

4. **Efficient Polling**
   - Only active during pending jobs
   - Automatic cleanup on completion
   - Exponential backoff on errors (TODO)

5. **State Batching**
   - useCallback for expensive functions
   - Refs for values that don't need re-render
   - Debounced audio level updates

### Memory Management

```typescript
// Cleanup on unmount
useEffect(() => {
  return () => {
    if (fullAudioUrlRef.current) {
      URL.revokeObjectURL(fullAudioUrlRef.current);
    }
  };
}, []);

// Cleanup on new recording
if (fullAudioUrlRef.current) {
  URL.revokeObjectURL(fullAudioUrlRef.current);
  fullAudioUrlRef.current = null;
  setFullAudioUrl(null);
}
```

## Testing

### Manual Test Checklist

- [ ] Start recording - verify audio level visualization
- [ ] Speak for 10 seconds - verify real-time transcription
- [ ] Stop recording - verify full audio playback
- [ ] Click "Continuar" - verify HDF5 modal appears
- [ ] Check chunk timeline - verify colors match states
- [ ] Expand "Métricas Avanzadas" - verify latency/WPM
- [ ] Play demo audio - verify pause/resume works
- [ ] Record while demo plays - verify simultaneous operation
- [ ] Stop without speaking - verify empty state handling

### Known Issues

1. **Hot-reload with useCallback**
   - Sometimes requires full page refresh
   - Fixed by restarting dev server

2. **Backend 404 on /inspect**
   - Falls back to local data
   - Modal still works with client-side info

## Future Enhancements

### High Priority
- [ ] Add speaker diarization visualization
- [ ] Export session data as JSON/PDF
- [ ] Add retry mechanism for failed chunks
- [ ] Implement exponential backoff on polling errors

### Medium Priority
- [ ] Add audio waveform visualization
- [ ] Support multiple audio formats (WAV, MP3)
- [ ] Add language selection (es-MX, en-US, etc.)
- [ ] Implement session resume (continue recording)

### Low Priority
- [ ] Add keyboard shortcuts (Space = pause/resume)
- [ ] Add dark/light theme toggle
- [ ] Export activity logs
- [ ] Add video recording support

## Troubleshooting

### Issue: Transcription not appearing
**Cause**: Polling endpoint incorrect or backend not returning transcript field
**Solution**: Check console logs, verify `/api/workflows/aurity/jobs/{job_id}` response

### Issue: Full audio only plays first chunk
**Cause**: Using concatenated chunks instead of continuous recorder
**Solution**: Ensure `continuousRecorderRef` is properly initialized and used

### Issue: Demo button not working
**Cause**: CORS blocking static file access
**Solution**: Verify `CORSStaticFiles` wrapper in `backend/app/main.py`

### Issue: High latency (>5s per chunk)
**Cause**: Backend worker overloaded or Whisper model slow
**Solution**: Check backend logs, consider using smaller Whisper model

### Issue: Backend health shows "degraded"
**Cause**: Some API requests failing
**Solution**: Check network tab, verify backend is running on port 7001

## References

- **RecordRTC Library**: Used for chunked audio recording
- **Web Audio API**: Used for real-time audio level monitoring
- **HDF5 Schema**: `/sessions/{session_id}/ml_ready/text/chunks/chunk_{idx}`
- **AURITY Prompt**: AUR-PROMPT-4.2 (Chunk transcription layering)

## Changelog

### v2.0 (2025-11-12)
- ✅ Added dual recording system (chunked + continuous)
- ✅ Implemented real-time polling with animations
- ✅ Enhanced audio analysis with voice activity detection
- ✅ Added advanced monitoring panel (expandable)
- ✅ Implemented HDF5 data modal
- ✅ Added WPM calculation
- ✅ Added backend health monitoring
- ✅ Added activity logs
- ✅ Demo audio playback with pause/resume

### v1.0 (Previous)
- Basic recording functionality
- Simple transcription display
- Audio level visualization

---

**Maintained by**: Bernard Uriza Orozco
**Component**: ConversationCapture
**Framework**: React + Next.js 14 + TypeScript
**Backend**: FastAPI + Whisper + HDF5
