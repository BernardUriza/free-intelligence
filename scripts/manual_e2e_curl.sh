#!/usr/bin/env bash
set -euo pipefail

# Manual E2E curl script for PUBLIC -> INTERNAL(func) -> Personas -> traces -> SOAP -> finalize
# Usage: BASE="http://localhost:7001" ./scripts/manual_e2e_curl.sh

BASE=${BASE:-"https://app.aurity.io"}
JSON='Content-Type: application/json'
SID=${SID:-"$(uuidgen | tr 'A-Z' 'a-z')"}
OUTDIR="/tmp/fi_e2e_${SID}"
mkdir -p "$OUTDIR"

echo "Using BASE=$BASE SID=$SID OUTDIR=$OUTDIR"

echo "1) Health check"
curl -sS "$BASE/api/health" | tee "$OUTDIR/health.json" | jq .

echo "2) Dry-run (safe)"
curl -sS -H "$JSON" -X POST \
  "$BASE/api/workflows/aurity/assistant/chat/_dry-run" \
  -d '{
    "persona":"clinical_advisor",
    "message":"Paciente masculino 45a, HTA y cefalea intensa.",
    "response_mode":"concise",
    "rag_context":"RFC: ABCD900101XXX, creatinina 1.8 mg/dL, TA 180/110"
  }' | tee "$OUTDIR/dryrun.json" | jq .

RID=$(jq -r .request_id "$OUTDIR/dryrun.json" 2>/dev/null || echo "")
if [ -z "$RID" ]; then
  echo "ERROR: no request_id in dryrun output" >&2
else
  echo "Captured RID=$RID"
fi

echo "3) Trace for dry-run"
if [ -n "$RID" ]; then
  curl -sS "$BASE/api/workflows/aurity/assistant/chat/_trace/$RID" | tee "$OUTDIR/dryrun_trace.json" | jq .
fi

echo "4) Clinical conversation (persona + mode)"
curl -sS -H "$JSON" -X POST \
  "$BASE/api/workflows/aurity/assistant/chat" \
  -d '{
    "persona":"clinical_advisor",
    "message":"Paciente 45a con TA 180/110, cefalea y visión borrosa. ¿Conducta inicial?",
    "response_mode":"explanatory"
  }' | tee "$OUTDIR/chat1.json" | jq .

RID2=$(jq -r .request_id "$OUTDIR/chat1.json" 2>/dev/null || echo "")
if [ -n "$RID2" ]; then
  echo "Captured RID2=$RID2; fetching trace"
  curl -sS "$BASE/api/workflows/aurity/assistant/chat/_trace/$RID2" | tee "$OUTDIR/chat1_trace.json" | jq .
else
  echo "WARNING: no request_id in chat1 response"
fi

echo "5) Create session and upload chunk (simulated metadata only)"
curl -sS -X POST "$BASE/api/workflows/aurity/stream?sid=$SID&seq=1" \
  -F 'meta={"sample_rate":48000,"channels":1};type=application/json' \
  -F 'chunk=@-;type=application/octet-stream' <<'EOF' | tee "$OUTDIR/stream_resp.json" | jq .
SIMULATED_CHUNK
EOF

echo "6) Monitor session"
curl -sS "$BASE/api/workflows/aurity/sessions/$SID/monitor" | tee "$OUTDIR/monitor.json" | jq .

echo "7) Start diarization"
curl -sS -H "$JSON" -X POST \
  "$BASE/api/workflows/aurity/sessions/$SID/diarization" \
  -d '{"engine":"default"}' | tee "$OUTDIR/diarization.json" | jq .

echo "8) Generate SOAP"
curl -sS -H "$JSON" -X POST \
  "$BASE/api/workflows/aurity/sessions/$SID/soap" \
  -d '{
    "format":"json",
    "include_codes": true,
    "style":"concise"
  }' | tee "$OUTDIR/soap.json" | jq .

echo "9) Finalize session"
curl -sS -H "$JSON" -X POST \
  "$BASE/api/workflows/aurity/sessions/$SID/finalize" \
  -d '{"encrypt":true}' | tee "$OUTDIR/finalize.json" | jq .

echo "10) Negative tests"
echo "10a) Invalid persona"
curl -sS -H "$JSON" -X POST "$BASE/api/workflows/aurity/assistant/chat" -d '{"persona":"no_such_persona","message":"hola"}' | tee "$OUTDIR/neg_invalid_persona.json" | jq .

echo "10b) Simulate LLM timeout (if supported)"
curl -sS -H "$JSON" -X POST "$BASE/api/workflows/aurity/assistant/chat" -d '{"persona":"clinical_advisor","message":"#simulate_timeout"}' | tee "$OUTDIR/neg_timeout.json" | jq .

echo "11) Acceptance quick checks"
echo "Dry-run output summary:"
jq '{request_id:.request_id, user_message_hash8:.user_message.hash8, user_message_len:.user_message.length, system_markers:.system_markers}' "$OUTDIR/dryrun.json" | tee "$OUTDIR/dryrun_summary.json"

echo "Trace events (dryrun):"
jq '.events[]?.type' "$OUTDIR/dryrun_trace.json" | tee "$OUTDIR/dryrun_events.txt" || true

echo "SOAP keys:"
jq 'keys' "$OUTDIR/soap.json" | tee "$OUTDIR/soap_keys.txt" || true

echo "Finished. Outputs are in $OUTDIR"

exit 0
