#!/bin/bash
#
# Smoke Test for Triage API
# Card: FI-API-FEAT-014
#
# Usage: ./tests/smoke_test_triage.sh
#

set -e

BASE=${API_BASE:-http://localhost:7001}
OUTPUT_DIR="./ops/audit"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTPUT_FILE="${OUTPUT_DIR}/triage_${TIMESTAMP}_evidence.txt"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "========================================"
echo "  Triage API Smoke Test"
echo "========================================"
echo "BASE: $BASE"
echo "Timestamp: $TIMESTAMP"
echo ""

# Ensure output directory exists
mkdir -p "$OUTPUT_DIR"

# Test 1: Valid intake
echo -e "${YELLOW}Test 1: Valid triage intake${NC}"
PAY='{"reason":"consulta respiratoria","symptoms":["tos","fiebre","dolor de garganta"],"audioTranscription":"Paciente presenta tos seca desde hace 3 días","metadata":{"runId":"smoke_'${TIMESTAMP}'"}}'

HTTP_CODE=$(curl -s -o /tmp/tri_out.json -w "%{http_code}" \
  -H 'Content-Type: application/json' \
  -d "$PAY" \
  "$BASE/api/triage/intake")

echo "HTTP Code: $HTTP_CODE"

if [ "$HTTP_CODE" = "200" ]; then
  echo -e "${GREEN}✓ Status 200 OK${NC}"

  BUFFER_ID=$(jq -r '.bufferId' /tmp/tri_out.json)
  STATUS=$(jq -r '.status' /tmp/tri_out.json)
  RECEIVED_AT=$(jq -r '.receivedAt' /tmp/tri_out.json)
  MANIFEST_URL=$(jq -r '.manifestUrl' /tmp/tri_out.json)

  echo "Buffer ID: $BUFFER_ID"
  echo "Status: $STATUS"
  echo "Received At: $RECEIVED_AT"
  echo "Manifest URL: $MANIFEST_URL"

  # Verify bufferId format
  if [[ $BUFFER_ID =~ ^tri_[0-9a-f]{32}$ ]]; then
    echo -e "${GREEN}✓ BufferId format correct${NC}"
  else
    echo -e "${RED}✗ BufferId format incorrect${NC}"
    exit 1
  fi

  # Verify status
  if [ "$STATUS" = "received" ]; then
    echo -e "${GREEN}✓ Status is 'received'${NC}"
  else
    echo -e "${RED}✗ Status is not 'received'${NC}"
    exit 1
  fi

  # Test 2: Retrieve manifest
  echo ""
  echo -e "${YELLOW}Test 2: Retrieve manifest${NC}"
  MANIFEST_HTTP=$(curl -s -o /tmp/tri_manifest.json -w "%{http_code}" "$BASE$MANIFEST_URL")

  if [ "$MANIFEST_HTTP" = "200" ]; then
    echo -e "${GREEN}✓ Manifest retrieved (200 OK)${NC}"

    MANIFEST_VERSION=$(jq -r '.version' /tmp/tri_manifest.json)
    PAYLOAD_HASH=$(jq -r '.payloadHash' /tmp/tri_manifest.json)

    echo "Manifest Version: $MANIFEST_VERSION"
    echo "Payload Hash: $PAYLOAD_HASH"

    # Verify payload hash format
    if [[ $PAYLOAD_HASH =~ ^sha256:[0-9a-f]{64}$ ]]; then
      echo -e "${GREEN}✓ Payload hash format correct (sha256:...)${NC}"
    else
      echo -e "${RED}✗ Payload hash format incorrect${NC}"
      exit 1
    fi
  else
    echo -e "${RED}✗ Failed to retrieve manifest (HTTP $MANIFEST_HTTP)${NC}"
    exit 1
  fi

else
  echo -e "${RED}✗ Failed (HTTP $HTTP_CODE)${NC}"
  cat /tmp/tri_out.json
  exit 1
fi

# Test 3: Validation - missing reason (expect 422)
echo ""
echo -e "${YELLOW}Test 3: Validation - missing reason (expect 422)${NC}"
PAY_INVALID='{"symptoms":["tos"]}'
INVALID_HTTP=$(curl -s -o /tmp/tri_invalid.json -w "%{http_code}" \
  -H 'Content-Type: application/json' \
  -d "$PAY_INVALID" \
  "$BASE/api/triage/intake")

if [ "$INVALID_HTTP" = "422" ]; then
  echo -e "${GREEN}✓ Validation rejected correctly (422)${NC}"
else
  echo -e "${RED}✗ Expected 422, got $INVALID_HTTP${NC}"
  exit 1
fi

# Test 4: Validation - transcription too long (expect 422)
echo ""
echo -e "${YELLOW}Test 4: Validation - transcription too long (expect 422)${NC}"
LONG_TEXT=$(python3 -c "print('a' * 33000)")
PAY_LONG=$(jq -n --arg text "$LONG_TEXT" '{"reason":"test","symptoms":["test"],"audioTranscription":$text}')
LONG_HTTP=$(curl -s -o /tmp/tri_long.json -w "%{http_code}" \
  -H 'Content-Type: application/json' \
  -d "$PAY_LONG" \
  "$BASE/api/triage/intake")

if [ "$LONG_HTTP" = "422" ]; then
  echo -e "${GREEN}✓ Transcription limit enforced (422)${NC}"
else
  echo -e "${RED}✗ Expected 422, got $LONG_HTTP${NC}"
  exit 1
fi

# Save evidence
echo ""
echo "========================================"
echo "  Evidence Summary"
echo "========================================"

cat > "$OUTPUT_FILE" << EOF
Triage API Smoke Test Evidence
Timestamp: $TIMESTAMP
BASE: $BASE

Test 1: Valid Intake
  HTTP Code: $HTTP_CODE
  Buffer ID: $BUFFER_ID
  Status: $STATUS
  Received At: $RECEIVED_AT
  Manifest URL: $MANIFEST_URL

Test 2: Manifest Retrieval
  HTTP Code: $MANIFEST_HTTP
  Manifest Version: $MANIFEST_VERSION
  Payload Hash: $PAYLOAD_HASH

Test 3: Validation - Missing Reason
  HTTP Code: $INVALID_HTTP (expected 422)

Test 4: Validation - Transcription Limit
  HTTP Code: $LONG_HTTP (expected 422)

All Tests: PASSED ✓
EOF

echo "Evidence saved to: $OUTPUT_FILE"
cat "$OUTPUT_FILE"

echo ""
echo -e "${GREEN}========================================"
echo -e "  All Tests PASSED ✓"
echo -e "========================================${NC}"
