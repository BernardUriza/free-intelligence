# Diarization Job History UI - Implementation Complete

**Card**: FI-RELIABILITY-IMPL-004
**Date**: 2025-10-31
**Status**: ✅ COMPLETED

## Summary

Added job history functionality to the diarization UI, allowing users to view all previously created jobs (including jobs that persist across backend restarts via HDF5 storage).

**Key Feature**: Jobs are now visible in the UI, stored persistently in HDF5, and can be clicked to view full details.

---

## Changes Made

### 1. Backend API (`backend/diarization_worker_lowprio.py`)

**Added Methods**:

**`list_all_jobs()` method** (lines 506-559):
- Reads all jobs from HDF5 `/diarization/` group
- Filters by `session_id` (optional)
- Returns metadata only (no `chunks[]` array for performance)
- Sorts by `created_at` descending (newest first)
- Supports limit parameter (default 50, UI uses 20)

**Module-level export** (lines 623-626):
```python
def list_all_jobs(session_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
    """List all diarization jobs from HDF5."""
    worker = get_worker()
    return worker.list_all_jobs(session_id, limit)
```

### 2. Backend REST API (`backend/api/diarization.py`)

**Updated Endpoint** (`GET /api/diarization/jobs`):
- Dual-mode: uses HDF5 when `USE_LOWPRIO_WORKER=true`, falls back to legacy in-memory
- Returns `{"jobs": [...], "count": N}` format
- Session ID filtering via query param `?session_id=xxx`
- Limit via query param `?limit=20`

**Contract**:
```bash
GET /api/diarization/jobs?session_id={uuid}&limit=20

Response:
{
  "jobs": [
    {
      "job_id": "uuid",
      "session_id": "uuid",
      "status": "completed",
      "progress_pct": 100,
      "total_chunks": 3,
      "processed_chunks": 3,
      "created_at": "2025-10-31T12:00:00Z",
      "updated_at": "2025-10-31T12:01:30Z",
      "error": null
    }
  ],
  "count": 1
}
```

### 3. Frontend API Client (`apps/aurity/lib/api/diarization.ts`)

**Restored Function** (lines 121-142):
```typescript
export async function listDiarizationJobs(
  sessionId?: string,
  limit: number = 20
): Promise<DiarizationJob[]>
```

**Note**: This was incorrectly removed as "legacy" in the previous update. User caught the mistake.

### 4. Frontend UI (`apps/aurity/app/diarization/page.tsx`)

**New State Management**:
```typescript
const [jobHistory, setJobHistory] = useState<DiarizationJob[]>([]);
const [loadingHistory, setLoadingHistory] = useState(true);
```

**Load History on Mount**:
```typescript
useEffect(() => {
  const loadHistory = async () => {
    try {
      setLoadingHistory(true);
      const jobs = await listDiarizationJobs(sessionId, 20);
      setJobHistory(jobs);
    } catch (err) {
      console.error('Failed to load job history:', err);
    } finally {
      setLoadingHistory(false);
    }
  };

  loadHistory();
}, [sessionId]);
```

**Reload History After Upload**:
- After successful job completion, UI reloads job list
- New job appears at top of history (newest first)

**View Job Handler**:
```typescript
const handleViewJob = async (jobId: string) => {
  try {
    setError(null);
    const jobDetails = await getDiarizationJobStatus(jobId);
    setJob(jobDetails);
    if (jobDetails.chunks) {
      setChunks(jobDetails.chunks);
    }
  } catch (err: any) {
    setError(`Failed to load job: ${err.message}`);
  }
};
```

**New UI Section** ("Historial de Jobs"):
- Displays after Upload section, before Progress section
- Loading state: "Cargando historial..."
- Empty state: "No hay jobs previos para esta sesión."
- Job cards show:
  - Status badge (color-coded: completed=green, in_progress=blue, pending=yellow, failed=red)
  - Job ID (truncated to 8 chars)
  - Created timestamp
  - Progress percentage
  - Chunks counter (processed / total)
  - Updated timestamp
  - Error message (if failed)
- Hover effect: border-blue, shadow
- Click handler: loads full job details into existing chunk display

---

## UI Flow

### Initial Load
1. User navigates to `/diarization`
2. `useEffect` triggers `listDiarizationJobs(sessionId, 20)`
3. Backend queries HDF5 `/diarization/*` groups
4. UI displays jobs sorted by creation time (newest first)

### Upload New Job
1. User uploads audio file
2. Job processes (incremental chunks appear)
3. Job completes
4. `handleUpload` calls `listDiarizationJobs()` again
5. New job appears at top of history

### View Previous Job
1. User clicks job card in history
2. `handleViewJob(job_id)` fetches full details via `/api/diarization/jobs/{job_id}`
3. Chunks load into existing display section
4. Export buttons become available (if completed)

---

## Key Decisions

### 1. Session-based Filtering
- Jobs filtered by `session_id` (UUID generated on page mount)
- Each browser session sees only its own jobs
- Multi-user support: different sessions don't see each other's jobs

### 2. Performance Optimization
- Job list endpoint excludes `chunks[]` array (metadata only)
- Full chunks loaded only when clicking specific job
- Prevents loading thousands of chunks when listing jobs

### 3. Persistent Storage
- Jobs stored in HDF5 `/diarization/{job_id}/` structure
- Survives backend restarts (unlike legacy in-memory storage)
- Worker can be stopped/restarted without losing job history

### 4. Dual-Mode Backend
- `USE_LOWPRIO_WORKER=true` → reads from HDF5
- `USE_LOWPRIO_WORKER=false` → falls back to legacy in-memory
- Backward compatibility preserved

---

## Bug Fixed: Numpy Type Serialization

**Issue**: Initial curl test failed with `TypeError("'numpy.int64' object is not iterable")`

**Root Cause**: HDF5 attrs return numpy types (`np.int64`, `np.float64`) which are not JSON-serializable.

**Fix** (`backend/diarization_worker_lowprio.py:527-533`):
```python
def decode_if_bytes(val):
    if isinstance(val, bytes):
        return val.decode('utf-8')
    # Convert numpy types to Python native types
    if hasattr(val, 'item'):  # numpy scalar
        return val.item()
    return val
```

**Additional conversions** (lines 552-554):
- `progress_pct`: Wrap in `int()`
- `total_chunks`: Wrap in `int()`
- `processed_chunks`: Wrap in `int()`

**Verification**:
```bash
curl -s http://localhost:7001/api/diarization/jobs | python3 -m json.tool
# ✅ Returns 7 jobs, all JSON-serializable

curl -s "http://localhost:7001/api/diarization/jobs?session_id=test-session" | python3 -m json.tool
# ✅ Returns 2 filtered jobs

curl -s "http://localhost:7001/api/diarization/jobs/test-full-001" | python3 -m json.tool
# ✅ Returns job with chunks array
```

---

## Testing

### Manual Testing Flow

1. **Start backend** (low-priority mode):
   ```bash
   cd /Users/bernardurizaorozco/Documents/free-intelligence
   export DIARIZATION_LOWPRIO=true
   export DIARIZATION_CPU_IDLE_THRESHOLD=10.0
   uvicorn backend.fi_consult_service:app --reload --port 7001
   ```

2. **Start frontend**:
   ```bash
   cd apps/aurity
   pnpm dev  # http://localhost:9000/diarization
   ```

3. **Test Scenarios**:
   - Navigate to `/diarization`
   - Verify "Historial de Jobs" section loads (empty state initially)
   - Upload audio file (e.g., Speech.mp3)
   - Wait for job to complete
   - Verify new job appears in history
   - Click job card → chunks should load in display section
   - Refresh page → job history should persist
   - Restart backend → job history should still be visible

### Expected Behavior

**Empty State**:
```
Historial de Jobs
No hay jobs previos para esta sesión.
```

**With Jobs**:
```
Historial de Jobs

┌─────────────────────────────────────────────────────────┐
│ [COMPLETED] 3f7b1c1f...        2025-10-31, 12:00:00 PM │
│ Progreso: 100%  Chunks: 3/3  Actualizado: 12:01:30 PM  │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ [IN_PROGRESS] 5271a73c...      2025-10-31, 11:55:00 AM │
│ Progreso: 66%  Chunks: 2/3  Actualizado: 11:56:15 AM   │
└─────────────────────────────────────────────────────────┘
```

---

## API Endpoints Summary

### List Jobs (Metadata Only)
```
GET /api/diarization/jobs
Query Params:
  - session_id (optional): Filter by session
  - limit (default 50): Max results

Response:
  - jobs[]: Array of job metadata (no chunks)
  - count: Total jobs returned
```

### Get Job Details (With Chunks)
```
GET /api/diarization/jobs/{job_id}

Response:
  - Full job object including chunks[] array
```

### Upload Audio
```
POST /api/diarization/upload
Headers:
  - X-Session-ID: {uuid}
Body:
  - audio: File (multipart/form-data)
Query Params:
  - language: null (auto-detect)
  - persist: false

Response:
  - job_id, session_id, status, message
```

---

## Architecture Benefits

### 1. Persistent Job History
- HDF5 storage means jobs survive:
  - Backend restarts
  - Worker crashes
  - System reboots (if HDF5 file preserved)

### 2. Incremental Results
- Jobs store chunks as they process
- UI can display partial results while processing
- Resume capability (if worker restarts mid-job)

### 3. Session Isolation
- Each browser session has unique `session_id` (UUIDv4)
- Jobs filtered by session → multi-user support
- No cross-contamination between users

### 4. Performance Optimization
- List endpoint returns metadata only
- Chunks loaded on-demand (click to view)
- Prevents memory issues with large job histories

---

## Files Modified

1. `backend/diarization_worker_lowprio.py` (added `list_all_jobs()` method + export)
2. `backend/api/diarization.py` (updated `/jobs` endpoint for HDF5)
3. `apps/aurity/lib/api/diarization.ts` (restored `listDiarizationJobs()`)
4. `apps/aurity/app/diarization/page.tsx` (added job history UI section)

---

## TypeScript Validation

**Diarization Errors**: ✅ 0 errors
**Unrelated Errors**: 4 errors (heroicons missing, pre-existing)

```bash
pnpm --filter ./apps/aurity exec tsc --noEmit | grep diarization
# Output: (no diarization errors)
```

---

## Feature: Ver Todas las Sesiones ✅

**Implementado**: 2025-10-31

Agregado toggle "Ver todas las sesiones" para mostrar jobs de todas las sesiones (no solo la actual).

**UI Changes** (`apps/aurity/app/diarization/page.tsx`):

```typescript
const [showAllSessions, setShowAllSessions] = useState(false);

// Load job history with optional session filter
useEffect(() => {
  const loadHistory = async () => {
    // Pass undefined to load ALL jobs when showAllSessions is true
    const jobs = await listDiarizationJobs(showAllSessions ? undefined : sessionId, 20);
    setJobHistory(jobs);
  };
  loadHistory();
}, [sessionId, showAllSessions]);
```

**UI Component**:
```jsx
<label className="flex items-center gap-2 text-sm cursor-pointer">
  <input
    type="checkbox"
    checked={showAllSessions}
    onChange={(e) => setShowAllSessions(e.target.checked)}
  />
  <span>Ver todas las sesiones</span>
</label>
```

**Behavior**:
- **Unchecked** (default): Shows only jobs from current session (UUIDv4 generated on page load)
- **Checked**: Shows ALL jobs in HDF5 (cross-session view)
- Empty state message adapts: "No hay jobs previos para esta sesión" vs "No hay jobs en el sistema"

**Use Cases**:
- Ver jobs creados en sesiones anteriores (reloads de página)
- Debugging: ver todos los jobs del sistema
- Admin view: monitorear todos los jobs de todos los usuarios

---

## Next Steps (Optional)

1. **Auto-Refresh**: Poll job history every 10s to show real-time status updates
2. **Delete Jobs**: Add trash icon to remove jobs from history
3. **Export from History**: Add export buttons to job cards (not just active job)
4. **Search/Filter**: Filter jobs by status (completed, failed, etc.)
5. **Pagination**: Load more than 20 jobs with "Load More" button
6. **Persist Session ID**: Save session_id in localStorage to maintain across reloads

---

## References

- **Backend Worker**: `backend/diarization_worker_lowprio.py`
- **Backend API**: `backend/api/diarization.py`
- **Frontend API Client**: `apps/aurity/lib/api/diarization.ts`
- **Frontend Page**: `apps/aurity/app/diarization/page.tsx`
- **Previous Docs**:
  - `DIARIZATION_UI_UPDATE.md` (incremental chunks)
  - `DIARIZATION_LOWPRIO.md` (low-priority worker architecture)

---

## User Feedback History

1. **Initial complaint**: "pero no veo los jobs ya creados aqui" (screenshot showed empty page)
2. **Caught my mistake**: "pero no es lo que marcaste como legacy?" (correctly identified that I removed needed function)
3. **Decision on approach**: "B" (chose HDF5 backend update over frontend-only solution)
4. **Final question**: "donde se ve listDiarizationJobs" (wanted to see UI implementation)

---

## License

MIT
