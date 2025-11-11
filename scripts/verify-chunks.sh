#!/usr/bin/env bash
#
# Chunk Quality Verification Script
# Verifies RecordRTC fix: Independent chunks with complete EBML headers
#
# Usage: ./scripts/verify-chunks.sh <session_id>
#

set -euo pipefail

SESSION_ID="${1:-}"
if [ -z "$SESSION_ID" ]; then
    echo "❌ Usage: $0 <session_id>"
    exit 1
fi

AUDIO_DIR="/Users/bernardurizaorozco/Documents/free-intelligence/storage/audio/$SESSION_ID"

if [ ! -d "$AUDIO_DIR" ]; then
    echo "❌ Session directory not found: $AUDIO_DIR"
    exit 1
fi

echo "🔍 CHUNK QUALITY VERIFICATION"
echo "Session: $SESSION_ID"
echo "=" | head -c 60
echo ""

TOTAL_CHUNKS=0
VALID_CHUNKS=0
INVALID_CHUNKS=0
HEADERLESS_CHUNKS=0

for chunk_file in "$AUDIO_DIR"/chunk_*.webm; do
    [ -e "$chunk_file" ] || continue

    CHUNK_NAME=$(basename "$chunk_file")
    CHUNK_NUM=$(echo "$CHUNK_NAME" | grep -oE '[0-9]+')
    SIZE=$(stat -f%z "$chunk_file" 2>/dev/null || stat -c%s "$chunk_file" 2>/dev/null)

    TOTAL_CHUNKS=$((TOTAL_CHUNKS + 1))

    echo ""
    echo "Chunk $CHUNK_NUM ($CHUNK_NAME)"
    echo "  Size: $SIZE bytes ($(echo "scale=1; $SIZE/1024" | bc) KB)"

    # Check for EBML magic bytes (0x1A45DFA3)
    HAS_HEADER=$(xxd -l 4 -p "$chunk_file" | grep -c "1a45dfa3" || echo "0")

    if [ "$HAS_HEADER" -eq 1 ]; then
        echo "  ✅ EBML Header: Present (0x1A45DFA3)"
    else
        echo "  ❌ EBML Header: MISSING (headerless chunk)"
        HEADERLESS_CHUNKS=$((HEADERLESS_CHUNKS + 1))
    fi

    # Check if ffprobe can read it
    DURATION=$(ffprobe -v error -show_entries format=duration \
        -of default=noprint_wrappers=1:nokey=1 \
        "$chunk_file" 2>/dev/null || echo "INVALID")

    if [ "$DURATION" != "INVALID" ] && [ -n "$DURATION" ]; then
        echo "  ✅ Duration: ${DURATION}s"

        # Check for corruption (duration < 0.5s is suspicious)
        if (( $(echo "$DURATION < 0.5" | bc -l) )); then
            echo "  ⚠️  WARNING: Duration too short (possible corruption)"
            INVALID_CHUNKS=$((INVALID_CHUNKS + 1))
        else
            VALID_CHUNKS=$((VALID_CHUNKS + 1))
        fi
    else
        echo "  ❌ Duration: INVALID (ffprobe failed)"
        INVALID_CHUNKS=$((INVALID_CHUNKS + 1))
    fi

    # Check audio content
    MAX_VOL=$(ffmpeg -i "$chunk_file" -af "volumedetect" -f null - 2>&1 | \
        grep "max_volume" | awk '{print $5}' || echo "N/A")

    if [ "$MAX_VOL" != "N/A" ]; then
        echo "  📊 Max Volume: ${MAX_VOL} dB"
    fi
done

echo ""
echo "=" | head -c 60
echo ""
echo "📊 SUMMARY"
echo "  Total chunks:      $TOTAL_CHUNKS"
echo "  ✅ Valid chunks:   $VALID_CHUNKS"
echo "  ❌ Invalid chunks: $INVALID_CHUNKS"
echo "  ⚠️  Headerless:    $HEADERLESS_CHUNKS"
echo ""

if [ "$HEADERLESS_CHUNKS" -gt 0 ]; then
    echo "❌ FAIL: Found headerless chunks (RecordRTC fix not applied)"
    echo "   Expected: All chunks have EBML headers"
    echo "   Action: Verify NEXT_PUBLIC_AURITY_FE_RECORDER=recordrtc in .env.local"
    exit 1
elif [ "$INVALID_CHUNKS" -gt 0 ]; then
    echo "⚠️  WARNING: Some chunks are invalid or corrupted"
    exit 1
else
    echo "✅ PASS: All chunks are valid with complete headers"
    exit 0
fi
