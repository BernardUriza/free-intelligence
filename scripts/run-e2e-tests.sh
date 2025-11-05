#!/bin/bash

set -e

echo "🎭 Playwright E2E Test Runner"
echo "=============================="
echo ""

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
FRONTEND_PORT=9000
BACKEND_PORT=7001
TEST_TIMEOUT=300

# Check if ports are in use
check_port() {
  if nc -z localhost "$1" 2>/dev/null; then
    return 0
  else
    return 1
  fi
}

# Print section
print_section() {
  echo ""
  echo -e "${BLUE}▶ $1${NC}"
}

print_success() {
  echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
  echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
  echo -e "${RED}❌ $1${NC}"
}

# Main execution
print_section "Checking Prerequisites"

# Check if pnpm is installed
if ! command -v pnpm &> /dev/null; then
  print_error "pnpm not found. Installing..."
  npm install -g pnpm
fi
print_success "pnpm found"

# Check if Playwright is installed
if ! pnpm list @playwright/test > /dev/null 2>&1; then
  print_error "@playwright/test not installed"
  exit 1
fi
print_success "@playwright/test installed"

# Check if browsers are installed
print_section "Installing Playwright Browsers"
pnpm exec playwright install chromium firefox webkit

print_section "Checking Service Ports"

if check_port "$FRONTEND_PORT"; then
  print_warning "Frontend port $FRONTEND_PORT already in use (may be running)"
else
  print_warning "Frontend port $FRONTEND_PORT not in use - Playwright will start it"
fi

if check_port "$BACKEND_PORT"; then
  print_success "Backend port $BACKEND_PORT is running"
else
  print_warning "Backend port $BACKEND_PORT not in use"
fi

print_section "Running Tests"
echo "Test directory: ./e2e"
echo "Config: playwright.config.ts"
echo "Browsers: chromium, firefox, webkit"
echo ""

# Run tests with detailed output
pnpm exec playwright test \
  --project=chromium \
  --reporter=html,json,junit,list \
  --timeout=300000 \
  --max-failures=5 \
  2>&1

TEST_EXIT_CODE=$?

print_section "Test Summary"

if [ $TEST_EXIT_CODE -eq 0 ]; then
  print_success "All tests passed!"
else
  print_warning "Some tests failed or had issues (exit code: $TEST_EXIT_CODE)"
fi

print_section "Reports Generated"
echo "📊 HTML Report: ./playwright-report/index.html"
echo "📋 JSON Report: ./test-results/results.json"
echo "📑 JUnit XML: ./test-results/results.xml"
echo ""

# Try to open HTML report
if command -v open &> /dev/null; then
  print_section "Opening HTML Report"
  open ./playwright-report/index.html &
  print_success "Report opened in default browser"
elif command -v xdg-open &> /dev/null; then
  xdg-open ./playwright-report/index.html &
  print_success "Report opened in default browser"
else
  print_warning "Could not automatically open report"
fi

print_section "Test Run Complete"
exit $TEST_EXIT_CODE
