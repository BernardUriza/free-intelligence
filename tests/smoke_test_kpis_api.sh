#!/bin/bash
#
# KPIs API Smoke Test
#
# Tests /api/kpis endpoint with all views and validates DoD requirements.
#
# File: tests/smoke_test_kpis_api.sh
# Created: 2025-10-30
# Card: FI-API-FEAT-011

set -e

BASE="${API_BASE:-http://localhost:7001}"
PASS=0
FAIL=0

echo "========================================"
echo "KPIs API Smoke Test"
echo "========================================"
echo "Base URL: $BASE"
echo ""

# Helper function to test endpoint
test_endpoint() {
  local name="$1"
  local url="$2"
  local expected_key="$3"

  echo -n "Testing $name... "

  response=$(curl -s "$url")
  exit_code=$?

  if [ $exit_code -ne 0 ]; then
    echo "❌ FAIL (curl error)"
    FAIL=$((FAIL + 1))
    return 1
  fi

  # Check if response contains expected key
  if echo "$response" | python3 -c "import sys, json; data=json.load(sys.stdin); sys.exit(0 if '$expected_key' in data else 1)" 2>/dev/null; then
    echo "✅ PASS"
    PASS=$((PASS + 1))
  else
    echo "❌ FAIL (missing key: $expected_key)"
    echo "Response: $response"
    FAIL=$((FAIL + 1))
    return 1
  fi
}

# Generate some HTTP traffic
echo "Generating traffic..."
for i in {1..20}; do
  curl -s "$BASE/api/sessions?limit=5" > /dev/null
done
echo ""

# Test 1: Summary view
test_endpoint "Summary view (5m)" "$BASE/api/kpis?window=5m&view=summary" "requests"

# Test 2: Chips view
test_endpoint "Chips view (5m)" "$BASE/api/kpis?window=5m&view=chips" "chips"

# Test 3: Timeseries view
test_endpoint "Timeseries view (15m)" "$BASE/api/kpis?window=15m&view=timeseries" "series"

# Test 4: Different windows
test_endpoint "Summary view (1m)" "$BASE/api/kpis?window=1m&view=summary" "latency"
test_endpoint "Summary view (1h)" "$BASE/api/kpis?window=1h&view=summary" "tokens"

# Test 5: Provider filter (should work even if no data)
test_endpoint "Provider filter (anthropic)" "$BASE/api/kpis?window=5m&provider=anthropic" "providers"

# Test 6: Performance test (p95 < 10ms)
echo -n "Testing p95 latency (<10ms)... "

latencies=""
for i in {1..40}; do
  latency=$(curl -s -o /dev/null -w "%{time_total}" "$BASE/api/kpis?window=5m&view=summary")
  latencies="$latencies$latency\n"
done

p95=$(echo -e "$latencies" | sort -n | awk '{a[NR]=$1} END{idx=int(0.95*NR); printf "%.0f", a[idx]*1000}')

if [ "$p95" -lt 10 ]; then
  echo "✅ PASS (p95: ${p95}ms)"
  PASS=$((PASS + 1))
else
  echo "❌ FAIL (p95: ${p95}ms, threshold: 10ms)"
  FAIL=$((FAIL + 1))
fi

# Test 7: Validate response structure
echo -n "Testing response structure... "

summary=$(curl -s "$BASE/api/kpis?window=5m&view=summary")

# Check all required keys
required_keys="window asOf requests latency tokens cache providers"
structure_valid=true

for key in $required_keys; do
  if ! echo "$summary" | python3 -c "import sys, json; data=json.load(sys.stdin); sys.exit(0 if '$key' in data else 1)" 2>/dev/null; then
    echo "❌ FAIL (missing key: $key)"
    FAIL=$((FAIL + 1))
    structure_valid=false
    break
  fi
done

if [ "$structure_valid" = true ]; then
  echo "✅ PASS"
  PASS=$((PASS + 1))
fi

# Summary
echo ""
echo "========================================"
echo "Results: $PASS passed, $FAIL failed"
echo "========================================"

if [ $FAIL -eq 0 ]; then
  echo "✅ ALL TESTS PASSED"
  exit 0
else
  echo "❌ SOME TESTS FAILED"
  exit 1
fi
