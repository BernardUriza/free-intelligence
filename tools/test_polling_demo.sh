#!/bin/bash
# Demo script to test polling agent
# Author: Bernard Uriza Orozco
# Created: 2025-11-14

set -e

echo "🧪 Polling Agent Demo"
echo "===================="
echo ""
echo "This script demonstrates the polling agent by:"
echo "1. Creating a test session_id file"
echo "2. Running the polling agent"
echo ""
echo "Prerequisites:"
echo "- Backend API must be running on http://localhost:7001"
echo "- A transcription job must exist for the session_id"
echo ""

# Cleanup
cleanup() {
    echo ""
    echo "🧹 Cleaning up..."
    rm -f /tmp/patient_session_id.txt
}
trap cleanup EXIT

# Get session ID from user
read -p "Enter session_id to monitor (or press Enter to use test ID): " SESSION_ID

if [ -z "$SESSION_ID" ]; then
    SESSION_ID="session_20251114_000000"
    echo "Using test ID: $SESSION_ID"
fi

# Write session ID to trigger file
echo "$SESSION_ID" > /tmp/patient_session_id.txt
echo "✅ Wrote session ID to /tmp/patient_session_id.txt"
echo ""

# Run polling agent
echo "🚀 Starting polling agent..."
echo ""
python3 tools/poll_transcription_progress.py

# Exit code
EXIT_CODE=$?
echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ Polling completed successfully"
else
    echo "❌ Polling failed with exit code $EXIT_CODE"
fi

exit $EXIT_CODE
