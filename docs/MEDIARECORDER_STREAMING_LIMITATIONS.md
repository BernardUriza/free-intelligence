# MediaRecorder Streaming Limitations & Solutions

**Card**: AUR-PROMPT-3.3
**Date**: 2025-11-09
**Status**: Documented Issue + Mitigation

## 🔴 Problem

### Observed Behavior

When using `MediaRecorder` with `timeslice` for real-time chunk streaming:

```javascript
const mediaRecorder = new MediaRecorder(stream, {
  mimeType: 'audio/webm;codecs=opus'
});
mediaRecorder.start(3000); // Request chunks every 3 seconds
```

**Expected**: Each chunk contains valid WebM container with EBML header
**Actual**:
- ❌ Chunk 0: Missing EBML header (raw Opus data)
- ❌ Chunk N>0: Missing EBML header (raw Opus data)

### Validation

```bash
# Check chunk 0
hexdump -C storage/audio/{session_id}/0.webm | head -3
# Expected: 1A 45 DF A3 (EBML magic)
# Actual: 43 C3 81 0B (raw Opus frame)

ffprobe storage/audio/{session_id}/0.webm
# Error: EBML header parsing failed
# Error: Invalid data found when processing input
```

### Root Cause

Per [MediaRecorder spec](https://www.w3.org/TR/mediastream-recording/):

> When multiple Blobs are returned (timeslice/requestData), individual Blobs **need not be playable**, but the combination of all Blobs MUST be playable.

**Chrome/Firefox behavior**: Emit raw codec frames without WebM container when using `timeslice`, even for chunk 0.

## 🛠️ Solutions

### 1. ✅ **Implemented: EBML Header Validation + Batch Fallback**

**File**: `apps/aurity/components/medical/ConversationCapture.tsx:203-226`

```typescript
// Validate chunk 0 has EBML header (0x1A45DFA3)
const hasValidEBMLHeader = async (blob: Blob): Promise<boolean> => {
  if (blob.size < 4) return false;
  const buffer = await blob.slice(0, 4).arrayBuffer();
  const view = new DataView(buffer);
  return view.getUint32(0, false) === 0x1A45DFA3;
};

// In processAudioChunk:
if (chunkNumber === 0) {
  const hasHeader = await hasValidEBMLHeader(chunkBlob);
  if (!hasHeader) {
    console.warn('⚠️ No EBML header - falling back to batch mode');
    return; // Skip streaming, process on mediaRecorder.onstop
  }
}
```

**Behavior**:
- ✅ Detects missing header in chunk 0
- ✅ Disables streaming gracefully
- ✅ Falls back to batch processing (all chunks combined on `onstop`)
- ✅ Shows user-friendly error: "Streaming no disponible, se usará modo batch"

### 2. 🔄 **Alternative: RecordRTC (Recommended for Production)**

**Library**: [recordrtc](https://www.npmjs.com/package/recordrtc)

```bash
npm install recordrtc
```

**Implementation**:

```typescript
import RecordRTC from 'recordrtc';

const recorder = new RecordRTC(stream, {
  type: 'audio',
  mimeType: 'audio/webm',
  recorderType: RecordRTC.StereoAudioRecorder,
  timeSlice: 3000, // 3 second chunks
  ondataavailable: async (blob) => {
    // ✅ Each blob is independently processable (has EBML header)
    await processAudioChunk(blob, chunkNumber, sessionId);
  },
  disableLogs: false
});

recorder.startRecording();
```

**Advantages**:
- ✅ Each chunk has proper EBML header + metadata
- ✅ Chunks are independently decodable by ffmpeg
- ✅ No 415/422 errors
- ✅ Works consistently across Chrome/Firefox/Safari
- ✅ Better control over encoding quality

**Disadvantages**:
- ⚠️ Additional dependency (55 KB gzipped)
- ⚠️ Requires migration from native MediaRecorder

### 3. 🔧 **Manual Header Extraction (Complex)**

**Concept**: Extract EBML header from a complete recording, then prepend to chunks.

```typescript
// 1. Record complete audio first
const completeRecording = await recordCompleteAudio(stream);

// 2. Extract header (everything before first Cluster: 0x1F43B675)
const extractHeader = (webmBytes: Uint8Array): Uint8Array => {
  const clusterMagic = new Uint8Array([0x1F, 0x43, 0xB6, 0x75]);
  let offset = 0;
  while (offset < webmBytes.length - 4) {
    if (webmBytes.slice(offset, offset + 4).every((b, i) => b === clusterMagic[i])) {
      return webmBytes.slice(0, offset);
    }
    offset++;
  }
  return webmBytes.slice(0, 4096); // Fallback: first 4KB
};

const header = extractHeader(new Uint8Array(await completeRecording.arrayBuffer()));

// 3. Prepend header to each chunk
const fixedChunk = new Blob([header, rawChunk], { type: 'audio/webm' });
```

**Issues**:
- ❌ Requires complete recording first (defeats streaming purpose)
- ❌ Cluster detection is fragile
- ❌ Header may not be compatible with chunks from different session

## 📊 Comparison

| Solution | Streaming | Independence | Complexity | Dependency |
|----------|-----------|--------------|------------|------------|
| **Batch Fallback** | ❌ No | N/A | Low | None |
| **RecordRTC** | ✅ Yes | ✅ Yes | Low | +55KB |
| **Manual Header** | ⚠️ Partial | ⚠️ Maybe | High | None |

## 🎯 Recommendation

### Immediate (MVP):
- ✅ Use **EBML validation + batch fallback** (already implemented)
- Acceptable UX: user records full session, processes at end

### Production (Phase 2):
- 🔄 Migrate to **RecordRTC** for true real-time streaming
- Benefits: Live transcription updates, speaker diarization in chunks

## 📚 References

- [MediaRecorder Spec](https://www.w3.org/TR/mediastream-recording/)
- [Stack Overflow: WebM chunks not independently playable](https://stackoverflow.com/questions/62236838/how-to-play-webm-files-individually-which-are-created-by-mediarecorder)
- [RecordRTC Documentation](https://recordrtc.org/)
- [WebM File Structure](https://permadi.com/2010/06/webm-file-structure/)
- [EBML Specification](https://matroska-org.github.io/libebml/)

## 🔬 Debug Commands

```bash
# Check if file has EBML header
hexdump -C file.webm | head -1
# Expected: 1a 45 df a3 ...

# Probe container
ffprobe -v error -show_streams file.webm

# Extract first 4KB (potential header)
dd if=chunk_0.webm of=header.bin bs=1 count=4096

# Search for Cluster element (0x1F43B675)
hexdump -C file.webm | grep "1f 43 b6 75"
```

## ✅ Testing

```bash
# Unit test: EBML header validation
npm test -- ConversationCapture.test.tsx -t "EBML header"

# Integration: Verify fallback behavior
# 1. Start recording in browser
# 2. Check console for "⚠️ No EBML header" warning
# 3. Verify batch processing on stop
```

---

**Status**: Issue documented, mitigation deployed
**Next Steps**: Evaluate RecordRTC for Phase 2 (FI-STRIDE Sprint 2)
