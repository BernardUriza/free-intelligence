#!/bin/bash
# Test runner for transcription service
# Usage: ./scripts/test-transcription.sh [options]

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Options
COVERAGE=false
WATCH=false
VERBOSE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --coverage)
            COVERAGE=true
            shift
            ;;
        --watch)
            WATCH=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -h|--help)
            echo "Test runner for transcription service"
            echo ""
            echo "Usage: ./scripts/test-transcription.sh [options]"
            echo ""
            echo "Options:"
            echo "  --coverage  Run with coverage report"
            echo "  --watch     Run in watch mode (auto-rerun on changes)"
            echo "  -v          Verbose output"
            echo "  -h          Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo -e "${BLUE}═══════════════════════════════════════════${NC}"
echo -e "${BLUE}Transcription Service Test Suite${NC}"
echo -e "${BLUE}═══════════════════════════════════════════${NC}"

# Check if pytest is installed
if ! python3 -m pytest --version >/dev/null 2>&1; then
    echo -e "${YELLOW}Installing test dependencies...${NC}"
    pip install -e ".[dev]"
fi

# Run tests
echo -e "\n${BLUE}Running tests...${NC}\n"

if [ "$WATCH" = true ]; then
    echo -e "${YELLOW}Watch mode enabled. Press Ctrl+C to exit.${NC}\n"
    pytest-watch backend/tests/test_transcription_service.py $([ "$VERBOSE" = true ] && echo "-v" || echo "")
elif [ "$COVERAGE" = true ]; then
    echo -e "${YELLOW}Running with coverage report...${NC}\n"
    pytest \
        backend/tests/test_transcription_service.py \
        --cov=backend.services.transcription_service \
        --cov=backend.whisper \
        --cov-report=term-missing \
        --cov-report=html \
        $([ "$VERBOSE" = true ] && echo "-v" || echo "")
    echo -e "\n${GREEN}✓ Coverage report saved to htmlcov/index.html${NC}"
else
    pytest \
        backend/tests/test_transcription_service.py \
        $([ "$VERBOSE" = true ] && echo "-v" || echo "")
fi

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo -e "\n${GREEN}═══════════════════════════════════════════${NC}"
    echo -e "${GREEN}✓ All tests passed!${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════${NC}"
else
    echo -e "\n${YELLOW}═══════════════════════════════════════════${NC}"
    echo -e "${YELLOW}✗ Some tests failed (exit code: $EXIT_CODE)${NC}"
    echo -e "${YELLOW}═══════════════════════════════════════════${NC}"
fi

exit $EXIT_CODE
