#!/bin/bash
# Test script for Celery + Redis integration (FI-BACKEND-ARCH-001)

set -e

PROJECT_ROOT="/Users/bernardurizaorozco/Documents/free-intelligence"
cd "$PROJECT_ROOT"

echo "🚀 Testing Celery + Redis Background Job Processing"
echo "=================================================="
echo ""

# Test audio file (use smaller Shakespeare file)
AUDIO_FILE="$HOME/Desktop/merchantofvenice_0_shakespeare_64kb.mp3"
SESSION_ID="session_celery_test_$(date +%s)"

if [ ! -f "$AUDIO_FILE" ]; then
    echo "❌ Test audio file not found: $AUDIO_FILE"
    echo "Please ensure the file exists or modify the AUDIO_FILE variable"
    exit 1
fi

echo "📤 Submitting job..."
echo "   Audio: $AUDIO_FILE"
echo "   Session: $SESSION_ID"
echo ""

# Submit job
RESPONSE=$(curl -s -X POST "http://localhost:7001/api/workflows/aurity/consult" \
  -H "X-Session-ID: $SESSION_ID" \
  -F "audio=@$AUDIO_FILE")

# Extract job_id
JOB_ID=$(echo "$RESPONSE" | jq -r '.job_id')
echo "✅ Job submitted!"
echo "   Job ID: $JOB_ID"
echo ""

# Wait a moment for Celery to pick up
sleep 3

echo "📊 Checking Celery Worker..."
docker logs --tail 50 fi-celery-worker 2>&1 | grep -E "(Received task|process_diarization|Task.*succeeded|Task.*failed)" | tail -5

echo ""
echo "🔍 Checking backend logs..."
tail -30 logs/backend-dev.log 2>/dev/null | grep -E "(WORKFLOW_WORKER|CELERY|task_id)" | tail -5

echo ""
echo "✅ Test complete! Check Flower UI at http://localhost:5555"
echo "   Job ID: $JOB_ID"
echo ""
echo "📊 To monitor task progress:"
echo "   watch -n 2 'docker logs --tail 20 fi-celery-worker 2>&1 | tail -10'"
