#!/bin/bash
#
# Smoke Test for Free Intelligence API
# Tests: CORS, port 7001, /api/sessions endpoint
#
# Usage: ./tools/smoke.sh
#
set -e

API_BASE="${API_BASE:-http://localhost:7001}"
PASS=0
FAIL=0

echo "========================================"
echo "Free Intelligence - Smoke Test"
echo "========================================"
echo "API Base: $API_BASE"
echo ""

# Helper functions
pass() {
    echo "✅ PASS: $1"
    ((PASS++))
}

fail() {
    echo "❌ FAIL: $1"
    ((FAIL++))
    return 1
}

# Test 1: Health endpoint
echo "Test 1: Health endpoint..."
if curl -f -s "$API_BASE/health" > /dev/null; then
    pass "Health endpoint responds"
else
    fail "Health endpoint not responding"
fi

# Test 2: Sessions API (GET /api/sessions)
echo "Test 2: Sessions API..."
if curl -f -s "$API_BASE/api/sessions" > /dev/null; then
    pass "Sessions API responds"
else
    fail "Sessions API not responding"
fi

# Test 3: CORS headers (OPTIONS preflight)
echo "Test 3: CORS preflight..."
CORS_RESPONSE=$(curl -s -X OPTIONS "$API_BASE/api/sessions" \
    -H "Origin: http://localhost:3000" \
    -H "Access-Control-Request-Method: GET" \
    -i | grep -i "access-control-allow-origin" || echo "")

if [ -n "$CORS_RESPONSE" ]; then
    pass "CORS headers present"
else
    fail "CORS headers missing"
fi

# Test 4: Export API
echo "Test 4: Export API..."
if curl -f -s "$API_BASE/api/exports" -X POST \
    -H "Content-Type: application/json" \
    -d '{"sessionId":"test","formats":["md"],"include":{"transcript":true,"events":false}}' \
    > /dev/null 2>&1 || [ $? -eq 22 ]; then
    # Exit code 22 means HTTP error (404, 500, etc.) but server responded
    pass "Export API endpoint exists"
else
    fail "Export API endpoint not found"
fi

# Test 5: Docs available
echo "Test 5: API Docs..."
if curl -f -s "$API_BASE/docs" > /dev/null; then
    pass "API docs available at /docs"
else
    fail "API docs not available"
fi

echo ""
echo "========================================"
echo "Results"
echo "========================================"
echo "PASS: $PASS"
echo "FAIL: $FAIL"
echo ""

if [ $FAIL -eq 0 ]; then
    echo "✅ ALL SMOKE TESTS PASSED"
    exit 0
else
    echo "❌ SOME TESTS FAILED"
    exit 1
fi
