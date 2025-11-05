#!/bin/bash
# Free Intelligence - Unified Development Startup Script
# Starts all services (Backend + Frontend) in a single terminal
#
# Usage: ./scripts/dev-all.sh
#
# Services:
#   - Backend API (port 7001) - FastAPI
#   - Frontend (port 9000) - Next.js

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo ""
echo "=========================================="
echo -e "${CYAN}Free Intelligence - Development Mode${NC}"
echo "=========================================="
echo ""

# Check prerequisites
check_prereqs() {
    echo -e "${BLUE}[1/4]${NC} Checking prerequisites..."

    # Check Node.js
    if ! command -v node &> /dev/null; then
        echo -e "${RED}❌ Node.js not found${NC}"
        echo "   Install Node.js 18+ from https://nodejs.org"
        exit 1
    fi
    NODE_VERSION=$(node -v)
    NODE_MAJOR=$(echo $NODE_VERSION | cut -d'v' -f2 | cut -d'.' -f1)
    if [ "$NODE_MAJOR" -lt 18 ]; then
        echo -e "${RED}❌ Node.js 18+ required (found $NODE_VERSION)${NC}"
        exit 1
    fi
    echo -e "   ${GREEN}✓${NC} Node.js $NODE_VERSION"

    # Check Python
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}❌ Python3 not found${NC}"
        echo "   Install Python 3.11+ from https://python.org"
        exit 1
    fi
    PYTHON_VERSION=$(python3 --version)
    echo -e "   ${GREEN}✓${NC} $PYTHON_VERSION"

    # Check pnpm
    if ! command -v pnpm &> /dev/null; then
        echo -e "${YELLOW}⚠️  pnpm not found${NC}"
        echo "   Installing pnpm globally..."
        npm install -g pnpm@latest
    fi
    PNPM_VERSION=$(pnpm -v)
    echo -e "   ${GREEN}✓${NC} pnpm $PNPM_VERSION"

    # Check make
    if ! command -v make &> /dev/null; then
        echo -e "${RED}❌ make not found${NC}"
        echo "   Install build tools for your platform"
        exit 1
    fi
    echo -e "   ${GREEN}✓${NC} make available"

    echo ""
}

# Install dependencies if needed
install_deps() {
    echo -e "${BLUE}[2/4]${NC} Checking dependencies..."

    # Check if node_modules exists
    if [ ! -d "node_modules" ] || [ ! -d "apps/aurity/node_modules" ]; then
        echo "   Installing Node.js dependencies..."
        pnpm install || {
            echo -e "${RED}❌ Failed to install Node.js dependencies${NC}"
            exit 1
        }
        echo -e "   ${GREEN}✓${NC} Node.js dependencies installed"
    else
        echo -e "   ${GREEN}✓${NC} Node.js dependencies OK"
    fi

    # Check Python dependencies
    if ! python3 -c "import fastapi" 2>/dev/null; then
        echo "   Installing Python dependencies..."
        pip install -e . || {
            echo -e "${RED}❌ Failed to install Python dependencies${NC}"
            exit 1
        }
        echo -e "   ${GREEN}✓${NC} Python dependencies installed"
    else
        echo -e "   ${GREEN}✓${NC} Python dependencies OK"
    fi

    echo ""
}

# Initialize storage
init_storage() {
    echo -e "${BLUE}[3/4]${NC} Initializing storage..."

    # Create directories
    mkdir -p storage logs data/triage_buffers data/diarization_jobs

    # Initialize corpus if needed
    if [ ! -f "storage/corpus.h5" ]; then
        echo "   Creating HDF5 corpus..."
        make init-corpus > /dev/null 2>&1 || true
        echo -e "   ${GREEN}✓${NC} Corpus initialized"
    else
        echo -e "   ${GREEN}✓${NC} Corpus exists"
    fi

    echo ""
}

# Cleanup function
cleanup() {
    echo ""
    echo -e "${YELLOW}Shutting down services...${NC}"

    # Kill background processes
    if [ -n "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null || true
    fi
    if [ -n "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null || true
    fi

    # Kill any remaining uvicorn/node processes on our ports
    lsof -ti:7001 | xargs kill -9 2>/dev/null || true
    lsof -ti:9000 | xargs kill -9 2>/dev/null || true

    echo -e "${GREEN}✓${NC} Services stopped"
    exit 0
}

# Register cleanup handler
trap cleanup SIGINT SIGTERM EXIT

# Start services
start_services() {
    echo -e "${BLUE}[4/4]${NC} Starting services..."
    echo ""

    # Start Backend API
    echo -e "${CYAN}🚀 Starting Backend API (port 7001)...${NC}"
    export PYTHONPATH="${PROJECT_ROOT}"
    python3 -m uvicorn backend.fi_consult_service:app \
        --host 0.0.0.0 \
        --port 7001 \
        --reload \
        --log-level info \
        > logs/backend-dev.log 2>&1 &
    BACKEND_PID=$!

    # Wait for backend to be ready
    echo -n "   Waiting for backend to start"
    for i in {1..15}; do
        if curl -s http://localhost:7001/health > /dev/null 2>&1; then
            echo ""
            echo -e "   ${GREEN}✓${NC} Backend API ready"
            break
        fi
        echo -n "."
        sleep 1
    done

    if ! curl -s http://localhost:7001/health > /dev/null 2>&1; then
        echo ""
        echo -e "   ${YELLOW}⚠️  Backend may still be starting...${NC}"
    fi

    echo ""

    # Start Frontend
    echo -e "${CYAN}🚀 Starting Frontend (port 9000)...${NC}"
    cd apps/aurity
    PORT=9000 pnpm dev > ../../logs/frontend-dev.log 2>&1 &
    FRONTEND_PID=$!
    cd ../..

    # Wait for frontend to be ready (Next.js 16+ can take longer)
    echo -n "   Waiting for frontend to start"
    for i in {1..30}; do
        if curl -s http://localhost:9000 > /dev/null 2>&1; then
            echo ""
            echo -e "   ${GREEN}✓${NC} Frontend ready"
            break
        fi
        echo -n "."
        sleep 1
    done

    if ! curl -s http://localhost:9000 > /dev/null 2>&1; then
        echo ""
        echo -e "   ${YELLOW}⚠️  Frontend still starting (Next.js 16 can be slower)...${NC}"
        echo -e "   ${YELLOW}   Check logs: tail -f logs/frontend-dev.log${NC}"
    fi

    echo ""
}

# Display info
show_info() {
    echo "=========================================="
    echo -e "${GREEN}✅ All Services Running${NC}"
    echo "=========================================="
    echo ""
    echo -e "${CYAN}Services:${NC}"
    echo "  • Backend API:  http://localhost:7001"
    echo "    └─ Docs:      http://localhost:7001/docs"
    echo "    └─ Health:    http://localhost:7001/health"
    echo ""
    echo "  • Frontend:     http://localhost:9000"
    echo "    └─ Dashboard: http://localhost:9000/dashboard"
    echo "    └─ Triage:    http://localhost:9000/triage"
    echo ""
    echo -e "${CYAN}Logs:${NC}"
    echo "  • Backend:  tail -f logs/backend-dev.log"
    echo "  • Frontend: tail -f logs/frontend-dev.log"
    echo ""
    echo -e "${CYAN}Process IDs:${NC}"
    echo "  • Backend PID:  $BACKEND_PID"
    echo "  • Frontend PID: $FRONTEND_PID"
    echo ""
    echo "=========================================="
    echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"
    echo "=========================================="
    echo ""
    echo -e "${CYAN}Stack:${NC}"
    echo "  • Next.js 16.0.1 (canary, better monorepo CSS support)"
    echo "  • React 19.2.0"
    echo "  • Tailwind CSS v3 with @tailwindcss/postcss"
    echo "  • pnpm 10.20.0"
    echo ""
}

# Monitor logs in real-time
monitor_logs() {
    # Use tail to follow both logs
    tail -f logs/backend-dev.log logs/frontend-dev.log 2>/dev/null || {
        # Fallback: just wait for Ctrl+C
        while true; do
            sleep 1
        done
    }
}

# Main execution
main() {
    check_prereqs
    install_deps
    init_storage
    start_services
    show_info
    monitor_logs
}

main
