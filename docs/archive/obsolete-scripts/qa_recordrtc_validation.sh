#!/bin/bash
# QA Validation Script for RecordRTC Migration (AUR-PROMPT-3.4)
# Tests EBML header presence, ffprobe decode, and latency

set -e

SID="${1:-test_session_$(date +%s)}"
AUDIO_DIR="storage/audio/$SID"

echo "🔬 QA Matrix: RecordRTC Chunk Validation"
echo "Session ID: $SID"
echo "Audio Dir: $AUDIO_DIR"
echo ""

if [ ! -d "$AUDIO_DIR" ]; then
  echo "❌ Session directory not found: $AUDIO_DIR"
  echo "💡 Record audio first with RecordRTC mode enabled"
  exit 1
fi

# 1. WebM Header Check
echo "1️⃣  WebM EBML Header Validation"
echo "   Expected: 1A 45 DF A3 (EBML magic number)"
echo ""

for file in "$AUDIO_DIR"/*.webm 2>/dev/null; do
  if [ -f "$file" ]; then
    basename=$(basename "$file")
    hex=$(hexdump -C "$file" | head -1 | awk '{print $2 $3 $4 $5}')

    if [ "$hex" = "1a45dfa3" ]; then
      echo "   ✅ $basename: Valid EBML header"
    else
      echo "   ❌ $basename: Missing/invalid EBML header (got: $hex)"
    fi
  fi
done

echo ""

# 2. ffprobe Decode Validation
echo "2️⃣  ffprobe Decode Test"
echo "   Testing all audio files can be probed"
echo ""

for file in "$AUDIO_DIR"/*.{webm,mp4,wav} 2>/dev/null; do
  if [ -f "$file" ]; then
    basename=$(basename "$file")

    if ffprobe -v error -show_streams -select_streams a:0 "$file" >/dev/null 2>&1; then
      echo "   ✅ $basename: Decode OK"
    else
      echo "   ❌ $basename: Decode FAILED"
    fi
  fi
done

echo ""

# 3. Latency Benchmark
echo "3️⃣  Latency Benchmark (ffmpeg to WAV conversion)"
echo "   Target: < 500ms per 3-second chunk"
echo ""

for i in {0..5}; do
  file="$AUDIO_DIR/${i}.webm"

  if [ -f "$file" ]; then
    start=$(python3 -c "import time; print(int(time.time() * 1000))")

    if ffmpeg -hide_banner -loglevel error -nostdin -y \
       -i "$file" -ac 1 -ar 16000 "/tmp/${SID}_${i}.wav" 2>/dev/null; then
      end=$(python3 -c "import time; print(int(time.time() * 1000))")
      latency=$((end - start))

      if [ $latency -lt 500 ]; then
        echo "   ✅ Chunk $i: ${latency}ms"
      else
        echo "   ⚠️  Chunk $i: ${latency}ms (slow)"
      fi
    else
      echo "   ❌ Chunk $i: ffmpeg conversion failed"
    fi
  fi
done

echo ""

# 4. Summary
echo "4️⃣  Summary"
echo ""

webm_count=$(find "$AUDIO_DIR" -name "*.webm" 2>/dev/null | wc -l | tr -d ' ')
mp4_count=$(find "$AUDIO_DIR" -name "*.mp4" 2>/dev/null | wc -l | tr -d ' ')
wav_count=$(find "$AUDIO_DIR" -name "*.wav" 2>/dev/null | wc -l | tr -d ' ')

echo "   Files found:"
echo "   - WebM: $webm_count"
echo "   - MP4:  $mp4_count"
echo "   - WAV:  $wav_count"
echo ""

if [ "$webm_count" -gt 0 ]; then
  echo "   💡 RecordRTC mode detected (WebM chunks present)"
elif [ "$mp4_count" -gt 0 ]; then
  echo "   💡 RecordRTC mode detected (MP4 chunks - Safari fallback)"
elif [ "$wav_count" -gt 0 ]; then
  echo "   💡 RecordRTC mode detected (WAV chunks)"
else
  echo "   ⚠️  No audio chunks found"
fi

echo ""
echo "✅ QA validation complete"
