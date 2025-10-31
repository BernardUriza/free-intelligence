#!/bin/bash
# Free Intelligence - NAS Deployment Readiness Check
# Validates that all deployment artifacts are present and executable
#
# Usage: ./scripts/validate-nas-deployment.sh

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo ""
echo "=========================================="
echo "Free Intelligence - Deployment Readiness"
echo "=========================================="
echo ""

CHECKS_PASSED=0
CHECKS_TOTAL=0

# Helper functions
check() {
    CHECKS_TOTAL=$((CHECKS_TOTAL + 1))
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓${NC} $2"
        CHECKS_PASSED=$((CHECKS_PASSED + 1))
    else
        echo -e "${RED}✗${NC} $2"
    fi
}

# Check 1: Docker Compose configs exist
CHECKS_TOTAL=$((CHECKS_TOTAL + 1))
if [ -f "docker-compose.ollama.yml" ] && [ -f "docker-compose.asr.yml" ]; then
    echo -e "${GREEN}✓${NC} Docker Compose configs present"
    CHECKS_PASSED=$((CHECKS_PASSED + 1))
else
    echo -e "${RED}✗${NC} Docker Compose configs missing"
fi

# Check 2: Deployment script executable
CHECKS_TOTAL=$((CHECKS_TOTAL + 1))
if [ -x "scripts/deploy-ds923.sh" ]; then
    echo -e "${GREEN}✓${NC} Deployment script executable"
    CHECKS_PASSED=$((CHECKS_PASSED + 1))
else
    echo -e "${RED}✗${NC} Deployment script not executable"
fi

# Check 3: ASR worker script executable
CHECKS_TOTAL=$((CHECKS_TOTAL + 1))
if [ -x "scripts/asr_worker.py" ]; then
    echo -e "${GREEN}✓${NC} ASR worker script executable"
    CHECKS_PASSED=$((CHECKS_PASSED + 1))
else
    echo -e "${RED}✗${NC} ASR worker script not executable"
fi

# Check 4: Environment example exists
CHECKS_TOTAL=$((CHECKS_TOTAL + 1))
if [ -f ".env.diarization.example" ]; then
    echo -e "${GREEN}✓${NC} Environment config example present"
    CHECKS_PASSED=$((CHECKS_PASSED + 1))
else
    echo -e "${RED}✗${NC} Environment config example missing"
fi

# Check 5: Validate Ollama compose syntax
CHECKS_TOTAL=$((CHECKS_TOTAL + 1))
if grep -q "fi-ollama" docker-compose.ollama.yml && grep -q "11434:11434" docker-compose.ollama.yml; then
    echo -e "${GREEN}✓${NC} Ollama config valid (port 11434, container name)"
    CHECKS_PASSED=$((CHECKS_PASSED + 1))
else
    echo -e "${RED}✗${NC} Ollama config invalid"
fi

# Check 6: Validate ASR compose syntax
CHECKS_TOTAL=$((CHECKS_TOTAL + 1))
if grep -q "fi-asr-worker" docker-compose.asr.yml && grep -q "faster-whisper" docker-compose.asr.yml; then
    echo -e "${GREEN}✓${NC} ASR config valid (faster-whisper, container name)"
    CHECKS_PASSED=$((CHECKS_PASSED + 1))
else
    echo -e "${RED}✗${NC} ASR config invalid"
fi

# Check 7: Deployment script has DoD validation
CHECKS_TOTAL=$((CHECKS_TOTAL + 1))
if grep -q "Smoke tests" scripts/deploy-ds923.sh && grep -q "api/generate" scripts/deploy-ds923.sh; then
    echo -e "${GREEN}✓${NC} Deployment script has smoke tests"
    CHECKS_PASSED=$((CHECKS_PASSED + 1))
else
    echo -e "${RED}✗${NC} Deployment script missing smoke tests"
fi

echo ""
echo "=========================================="
echo -e "Results: ${GREEN}${CHECKS_PASSED}/${CHECKS_TOTAL}${NC} checks passed"
echo "=========================================="
echo ""

if [ $CHECKS_PASSED -eq $CHECKS_TOTAL ]; then
    echo -e "${GREEN}✓ NAS deployment artifacts ready${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Copy to DS923+: scp -r . user@nas:/volume1/fi-app/"
    echo "  2. SSH into NAS: ssh user@nas"
    echo "  3. Run deployment: cd /volume1/fi-app && ./scripts/deploy-ds923.sh"
    echo ""
    exit 0
else
    echo -e "${RED}✗ Some checks failed - review artifacts${NC}"
    exit 1
fi
