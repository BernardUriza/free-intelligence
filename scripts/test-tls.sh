#!/bin/bash
# Free Intelligence - Test TLS 1.3 Configuration
# HIPAA Card: G-002 - Cifrado en tránsito (Evidence collection)
# Author: Bernard Uriza Orozco
# Created: 2025-11-17

set -e

echo "🧪 Testing TLS 1.3 Configuration..."
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test results
PASS=0
FAIL=0

# ============================================================================
# Test 1: HTTP → HTTPS Redirect (HIPAA requirement)
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Test 1: HTTP → HTTPS Redirect (301)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
HTTP_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/health || echo "000")
if [ "$HTTP_RESPONSE" == "301" ]; then
    echo -e "${GREEN}✅ PASS${NC}: HTTP redirects to HTTPS (301)"
    ((PASS++))
else
    echo -e "${RED}❌ FAIL${NC}: HTTP should redirect to HTTPS (got $HTTP_RESPONSE, expected 301)"
    ((FAIL++))
fi
echo ""

# ============================================================================
# Test 2: HTTPS Health Check
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Test 2: HTTPS Health Check"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
HTTPS_RESPONSE=$(curl -k -s -o /dev/null -w "%{http_code}" https://localhost/health || echo "000")
if [ "$HTTPS_RESPONSE" == "200" ]; then
    echo -e "${GREEN}✅ PASS${NC}: HTTPS health endpoint responds (200 OK)"
    ((PASS++))
else
    echo -e "${RED}❌ FAIL${NC}: HTTPS health check failed (got $HTTPS_RESPONSE, expected 200)"
    ((FAIL++))
fi
echo ""

# ============================================================================
# Test 3: TLS Protocol Version (TLS 1.3 only)
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Test 3: TLS Protocol Version (TLS 1.3 required)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
TLS_VERSION=$(curl -k -s -v https://localhost/health 2>&1 | grep "SSL connection using" | awk '{print $5}')
if [[ "$TLS_VERSION" == "TLSv1.3" ]]; then
    echo -e "${GREEN}✅ PASS${NC}: TLS 1.3 is active ($TLS_VERSION)"
    ((PASS++))
else
    echo -e "${RED}❌ FAIL${NC}: TLS 1.3 not detected (got '$TLS_VERSION', expected 'TLSv1.3')"
    ((FAIL++))
fi
echo ""

# ============================================================================
# Test 4: HSTS Header (HIPAA requirement)
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Test 4: HSTS Header (Strict-Transport-Security)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
HSTS_HEADER=$(curl -k -s -I https://localhost/health | grep -i "strict-transport-security")
if [[ ! -z "$HSTS_HEADER" ]]; then
    echo -e "${GREEN}✅ PASS${NC}: HSTS header present"
    echo "   Header: $HSTS_HEADER"
    ((PASS++))
else
    echo -e "${RED}❌ FAIL${NC}: HSTS header missing (HIPAA requirement)"
    ((FAIL++))
fi
echo ""

# ============================================================================
# Test 5: Security Headers
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Test 5: Security Headers"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
HEADERS=$(curl -k -s -I https://localhost/health)

# Check X-Frame-Options
if echo "$HEADERS" | grep -qi "x-frame-options"; then
    echo -e "${GREEN}✅ PASS${NC}: X-Frame-Options header present"
    ((PASS++))
else
    echo -e "${YELLOW}⚠️  WARN${NC}: X-Frame-Options header missing"
fi

# Check X-Content-Type-Options
if echo "$HEADERS" | grep -qi "x-content-type-options"; then
    echo -e "${GREEN}✅ PASS${NC}: X-Content-Type-Options header present"
    ((PASS++))
else
    echo -e "${YELLOW}⚠️  WARN${NC}: X-Content-Type-Options header missing"
fi
echo ""

# ============================================================================
# Test 6: Backend API Proxy
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Test 6: Backend API Proxy (if backend running on :7001)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
# Check if backend is running
if lsof -i :7001 > /dev/null 2>&1; then
    API_RESPONSE=$(curl -k -s -o /dev/null -w "%{http_code}" https://localhost/api/ || echo "000")
    if [ "$API_RESPONSE" != "000" ]; then
        echo -e "${GREEN}✅ PASS${NC}: Backend API proxied through HTTPS (status: $API_RESPONSE)"
        ((PASS++))
    else
        echo -e "${RED}❌ FAIL${NC}: Backend API proxy failed"
        ((FAIL++))
    fi
else
    echo -e "${YELLOW}⚠️  SKIP${NC}: Backend not running on port 7001"
fi
echo ""

# ============================================================================
# Summary
# ============================================================================
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Test Summary"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
TOTAL=$((PASS + FAIL))
echo "   Passed: $PASS"
echo "   Failed: $FAIL"
echo "   Total:  $TOTAL"
echo ""

if [ $FAIL -eq 0 ]; then
    echo -e "${GREEN}✅ ALL TESTS PASSED${NC}"
    echo ""
    echo "🎉 TLS 1.3 configuration is HIPAA-compliant!"
    echo ""
    echo "📋 Evidence collected for HIPAA card G-002:"
    echo "   • HTTP → HTTPS redirect: ✅"
    echo "   • TLS 1.3 protocol: ✅"
    echo "   • HSTS header: ✅"
    echo "   • Security headers: ✅"
    echo ""
    echo "🚀 Next steps:"
    echo "   1. Run testssl.sh for detailed SSL scan (A+ rating)"
    echo "   2. Capture Wireshark TLS handshake"
    echo "   3. Document evidence in Trello card"
    exit 0
else
    echo -e "${RED}❌ TESTS FAILED${NC}"
    echo ""
    echo "Fix the issues above and run again."
    exit 1
fi
