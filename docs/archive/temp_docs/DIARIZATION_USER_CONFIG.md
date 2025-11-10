# Diarization Configuration Guide

## Overview

The diarization page now includes a **Performance Configuration** panel where users can customize transcription settings in real-time. All settings are saved to browser storage and automatically applied to new uploads.

## Quick Access

1. Navigate to **Diarización de Audio** page
2. Click **▶ Mostrar Avanzado** to expand the configuration panel
3. Adjust settings and click "Subir Audio"
4. Configuration is automatically saved for future sessions

## Configuration Options

### 🎤 Modelo Whisper (Whisper Model)

Choose the ASR model that best fits your needs:

| Model | Speed | Accuracy | File Size | Use Case |
|-------|-------|----------|-----------|----------|
| **tiny** | 4-5x | ⭐ (basic) | 140MB | Very large files, speed critical |
| **base** | 2-3x | ⭐⭐⭐ (good) | 150MB | Default, recommended for most |
| **small** | 1x | ⭐⭐⭐⭐ (better) | 470MB | Balanced, production |
| **medium** | 0.5x | ⭐⭐⭐⭐⭐ (high) | 1.5GB | High accuracy, slower |
| **large-v3** | 0.2x | 🏆 (highest) | 3GB | Maximum accuracy, very slow |

**Recommendation:** Start with `base` for speed, upgrade to `small` if accuracy needed.

---

### 📦 Tamaño de Chunks (Chunk Size)

Controls how audio is split before transcription:

- **10-30s**: More granular, better speaker separation, slower processing
- **60s**: **Recommended default**, 25% faster than 30s
- **120s**: Very fast, coarser speaker boundaries

**Real-world impact:**
- 10-minute audio with 30s chunks: 20 chunks to transcribe
- 10-minute audio with 60s chunks: 10 chunks (50% fewer invocations)

**Recommendation:** `60s` for fast transcription, `30s` for precise speaker changes.

---

### 🤖 Clasificación LLM (LLM Speaker Classification)

Enable/disable automatic speaker role classification (PACIENTE/MÉDICO):

| Setting | Speed | Speaker Labels | Use Case |
|---------|-------|-----------------|----------|
| **Disabled** (◐) | 3-4x faster | DESCONOCIDO | Quick turnaround, sufficient labels |
| **Enabled** (✓) | Baseline | PACIENTE/MÉDICO | Clinical accuracy required |

When disabled:
- All speakers labeled as "DESCONOCIDO" (Unknown)
- Saves ~63% of processing time (LLM inference)
- Good for transcription-only workflows

When enabled:
- Whisper transcribes, Qwen LLM classifies each segment
- Adds speaker role context (patient vs doctor)
- Requires Ollama service running

**Recommendation:** Disable for speed, enable if you need speaker roles.

---

### 🎯 Beam Size

Controls Whisper transcription accuracy vs speed tradeoff:

| Beam Size | Speed | Accuracy | Notes |
|-----------|-------|----------|-------|
| **1** | 1.5x faster | Basic | Greedy decoding, fastest |
| **3** | Baseline | Good | Balance |
| **5** | 0.8x | Better | **Default**, recommended |
| **7** | 0.6x | High | Slower |
| **10+** | 0.3x | Highest | Slowest but most accurate |

- Higher beam_size = wider search space = better accuracy but slower
- For most use cases, `5` is optimal

**Recommendation:** Keep at `5`, adjust only if accuracy issues detected.

---

### 🔊 Voice Activity Detection (VAD)

Toggle automatic silence/noise filtering:

| Setting | Effect |
|---------|--------|
| **Enabled** (✓) | Filters silence and background noise, cleaner transcription |
| **Disabled** | Keeps all audio, may include noise/silence segments |

**Recommendation:** Keep enabled for medical consultations (removes background noise).

---

## Configuration Presets

### ⚡ Fast Mode (Default)

Best for large files, quick turnaround:
- Model: `base`
- Chunk Size: `60s`
- LLM Classification: **Disabled**
- Beam Size: `5`
- VAD: Enabled

**Speedup:** 5-6x vs. original

---

### ⚖️ Balanced Mode

Good balance for production use:
- Model: `small`
- Chunk Size: `30s`
- LLM Classification: **Enabled**
- Beam Size: `5`
- VAD: Enabled

**Speedup:** 1x (baseline, with speaker labels)

---

### 🎯 Accuracy Mode

Maximum quality, slower processing:
- Model: `large-v3`
- Chunk Size: `20s`
- LLM Classification: **Enabled**
- Beam Size: `10`
- VAD: Enabled

**Speedup:** 0.2x (5x slower, but highest accuracy)

---

### 🚀 Extreme Fast Mode

Maximum speed for very large files:
- Model: `tiny`
- Chunk Size: `120s`
- LLM Classification: **Disabled**
- Beam Size: `1`
- VAD: Enabled

**Speedup:** 10x vs. original

---

## Real-Time Speedup Calculator

The **Speedup Est.** card (green highlight) shows combined effect:

```
Base: 1x
Model: base (2.5x) → 2.5x total
LLM disabled (3.5x) → 8.75x total
Chunks: 60s (1.25x) → 10.9x total
```

Speedup is estimated; actual results depend on:
- Audio duration
- Audio quality
- CPU performance
- System load

---

## Common Use Cases

### 📋 Quick Consultation Transcription
**Goal:** Fast transcription, don't need speaker roles
- Model: `base`
- Chunk Size: `60s`
- LLM: **Disabled**
- **Result:** 5-6x faster

### 👨‍⚕️ Clinical Documentation
**Goal:** Accurate transcription with speaker labels
- Model: `small`
- Chunk Size: `30s`
- LLM: **Enabled**
- **Result:** Baseline with speaker context

### 📚 Research/Detailed Analysis
**Goal:** Maximum accuracy for analysis
- Model: `large-v3`
- Chunk Size: `20s`
- LLM: **Enabled**
- Beam Size: `10`
- **Result:** Highest quality, ~5x slower

### 🚀 Batch Processing Large Files
**Goal:** Process many files overnight
- Model: `tiny`
- Chunk Size: `120s`
- LLM: **Disabled**
- **Result:** 10x faster processing

---

## Storage & Persistence

### Browser Storage
- Configuration saved to **localStorage**
- Persists across browser sessions
- Survives page refreshes
- Specific to this browser/device

### Reset to Defaults
- Click **"↺ Resetear a valores por defecto"** to restore defaults
- All settings reset to Fast Mode (default)
- Can be done anytime before upload

---

## Performance Expectations

### 10-Minute Audio File (CPU: DS923+ Ryzen R1600)

| Configuration | Time | RTF |
|---------------|------|-----|
| Tiny + 120s + no LLM | 18s | 0.03x |
| Base + 60s + no LLM | 35s | 0.06x |
| Small + 30s + LLM | 180s | 0.30x |
| Large-v3 + 20s + LLM | 900s | 1.50x |

**RTF = Real-Time Factor** (1.0x = processes in real-time, 0.5x = 2x faster than real-time)

---

## Troubleshooting

### "Why is my transcription slow?"
1. Check if LLM is enabled → Disable for 3-4x speedup
2. Check chunk size → Increase to 60-120s
3. Check model size → Reduce to `base` or `tiny`

### "Why are speaker labels wrong?"
1. LLM classification may struggle with accents/dialects
2. Try enabling with `small` or `large-v3` model
3. Or just use with LLM disabled (still get transcription)

### "How do I get the best accuracy?"
1. Use `large-v3` model
2. Enable LLM classification
3. Reduce chunk size to 20s
4. Increase beam size to 10

### "Configuration not saving?"
1. Check if localStorage is enabled in browser
2. Clear browser cache and reload
3. Try a different browser

---

## Technical Details

### Configuration Format (JSON)
```json
{
  "whisperModel": "base",
  "enableLlmClassification": false,
  "chunkSizeSec": 60,
  "beamSize": 5,
  "vadFilter": true
}
```

### API Parameters
Configuration is sent to backend as query parameters:
```
POST /api/diarization/upload?whisper_model=base&enable_llm_classification=false&chunk_size_sec=60&beam_size=5&vad_filter=true
```

### Environment Variables (Backend)
Backend defaults (can be overridden per-request):
```bash
WHISPER_MODEL_SIZE=base
WHISPER_BEAM_SIZE=5
DIARIZATION_CHUNK_SEC=60
ENABLE_LLM_CLASSIFICATION=false
WHISPER_VAD_FILTER=true
```

---

## References

- **Performance Analysis:** See `PERFORMANCE_QUICK_WINS.yaml` for detailed breakdown
- **Whisper Docs:** https://github.com/openai/whisper
- **Qwen LLM:** https://huggingface.co/Qwen/Qwen2.5-7B-Instruct
- **Backend Config:** `backend/diarization_service.py`, `backend/whisper_service.py`

---

**Last Updated:** 2025-10-31
**Version:** 1.0 (User-Configurable Settings)
