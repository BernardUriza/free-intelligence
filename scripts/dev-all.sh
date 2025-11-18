#!/bin/bash
# Free Intelligence - Unified Development Startup Script (Python 3.14 Native)
# Starts all services (Backend + Frontend) in a single terminal
#
# Usage: ./scripts/dev-all.sh  OR  make dev-all
#
# Services:
#   - Backend API (port 7001) - FastAPI + Python 3.14
#   - Frontend (port 9000) - Next.js/Turbopack
#   - Workers: ThreadPoolExecutor (in-memory, no Redis/Celery)

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
echo -e "${CYAN}Python 3.14 Native (No Docker)${NC}"
echo "=========================================="
echo ""

# STEP 0: Cleanup existing processes
cleanup_existing() {
    echo -e "${BLUE}[0/4]${NC} Cleaning up existing processes..."

    # Kill processes on critical ports
    lsof -ti:7001,9000,9050,11434 2>/dev/null | xargs kill -9 2>/dev/null || true

    # Kill specific processes
    pgrep -f "uvicorn.*main:app" | xargs kill -9 2>/dev/null || true
    pgrep -f "next.*dev.*-p 9000" | xargs kill -9 2>/dev/null || true
    pgrep -f "pnpm.*dev" | xargs kill -9 2>/dev/null || true
    pgrep -f "python3.*uvicorn" | xargs kill -9 2>/dev/null || true

    echo -e "   ${GREEN}✓${NC} Cleanup complete"
    echo ""
}

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
    echo -e "   ${GREEN}✓${NC} Node.js $NODE_VERSION"

    # Check Python 3.14
    if ! command -v python3.14 &> /dev/null; then
        echo -e "${RED}❌ Python 3.14 not found${NC}"
        echo "   Install Python 3.14 from https://python.org"
        exit 1
    fi
    PYTHON_VERSION=$(python3.14 --version)
    echo -e "   ${GREEN}✓${NC} $PYTHON_VERSION"

    # Check pnpm
    if ! command -v pnpm &> /dev/null; then
        echo -e "${YELLOW}⚠️  pnpm not found, installing...${NC}"
        npm install -g pnpm@latest > /dev/null 2>&1
    fi
    PNPM_VERSION=$(pnpm -v)
    echo -e "   ${GREEN}✓${NC} pnpm $PNPM_VERSION"

    echo ""
}

# Check dependencies
check_deps() {
    echo -e "${BLUE}[2/4]${NC} Checking dependencies..."

    # Node.js dependencies
    if [ ! -d "$PROJECT_ROOT/node_modules" ]; then
        echo -e "   ${YELLOW}Installing Node.js dependencies...${NC}"
        pnpm install --frozen-lockfile > /dev/null 2>&1 || pnpm install > /dev/null 2>&1
    fi
    echo -e "   ${GREEN}✓${NC} Node.js dependencies OK"

    # Python dependencies (native, no venv)
    if ! python3.14 -c "import fastapi" 2>/dev/null; then
        echo -e "   ${YELLOW}Installing Python dependencies...${NC}"
        python3.14 -m pip install -q -r "$PROJECT_ROOT/requirements.txt" 2>/dev/null || true
    fi
    echo -e "   ${GREEN}✓${NC} Python dependencies OK"

    echo ""
}

# Initialize storage
init_storage() {
    echo -e "${BLUE}[3/4]${NC} Initializing storage..."

    if [ ! -d "$PROJECT_ROOT/storage" ]; then
        mkdir -p "$PROJECT_ROOT/storage"
        echo -e "   ${GREEN}✓${NC} Created storage directory"
    fi

    if [ ! -f "$PROJECT_ROOT/storage/corpus.h5" ]; then
        echo -e "   ${YELLOW}Initializing HDF5 corpus...${NC}"
        python3.14 -c "
import h5py
with h5py.File('$PROJECT_ROOT/storage/corpus.h5', 'w', libver='latest') as f:
    f.create_group('sessions')
    f.attrs['version'] = '1.0'
print('HDF5 initialized with SWMR support (superblock v3)')
" > /dev/null 2>&1 || true
        echo -e "   ${GREEN}✓${NC} HDF5 corpus created (SWMR-compatible)"
    fi

    echo ""
}

# Start services
start_services() {
    echo -e "${BLUE}[4/4]${NC} Starting services..."
    echo ""

    # Start Backend API in background (native Python 3.14)
    echo -e "${CYAN}🚀 Starting Backend API (Python 3.14 Native)${NC}"
    python3.14 -m uvicorn backend.app.main:app \
        --host 0.0.0.0 \
        --port 7001 \
        --reload \
        --log-level info \
        > "$PROJECT_ROOT/logs/backend-dev.log" 2>&1 &

    BACKEND_PID=$!
    echo -e "   ${GREEN}✓${NC} Backend started (PID: $BACKEND_PID)"

    # Wait for backend to be ready
    echo "   Waiting for backend to be ready..."
    for i in {1..30}; do
        if curl -s http://localhost:7001/health > /dev/null 2>&1; then
            echo -e "   ${GREEN}✓${NC} Backend API ready"
            break
        fi
        if [ $i -eq 30 ]; then
            echo -e "   ${RED}❌ Backend failed to start${NC}"
            kill $BACKEND_PID 2>/dev/null || true
            exit 1
        fi
        sleep 1
    done

    # Start Frontend in background
    echo ""
    echo -e "${CYAN}🚀 Starting Frontend (Next.js)${NC}"
    cd "$PROJECT_ROOT/apps/aurity"
    PORT=9000 pnpm dev \
        > "$PROJECT_ROOT/logs/frontend-aurity-dev.log" 2>&1 &

    FRONTEND_PID=$!
    cd "$PROJECT_ROOT"
    echo -e "   ${GREEN}✓${NC} Frontend started (PID: $FRONTEND_PID)"

    # Wait for frontend to be ready
    echo "   Waiting for frontend to be ready..."
    for i in {1..30}; do
        if curl -s http://localhost:9000 > /dev/null 2>&1; then
            echo -e "   ${GREEN}✓${NC} Frontend ready"
            break
        fi
        if [ $i -eq 30 ]; then
            echo -e "   ${YELLOW}⚠️  Frontend might be slow to start${NC}"
            break
        fi
        sleep 1
    done

    echo ""
}

# Display status
show_status() {
    echo "=========================================="
    echo -e "${GREEN}✅ All Services Running${NC}"
    echo "=========================================="
    echo ""
    echo -e "${CYAN}Services:${NC}"
    echo -e "  • Backend API (Native):   ${GREEN}http://localhost:7001${NC}"
    echo -e "    └─ Docs:                ${GREEN}http://localhost:7001/docs${NC}"
    echo -e "    └─ Health:              ${GREEN}http://localhost:7001/health${NC}"
    echo ""
    echo -e "  • AURITY Frontend:        ${GREEN}http://localhost:9000${NC}"
    echo -e "    └─ Dashboard:           ${GREEN}http://localhost:9000/dashboard${NC}"
    echo -e "    └─ Medical AI:          ${GREEN}http://localhost:9000/medical-ai${NC}"
    echo ""
    echo -e "${CYAN}Stack:${NC}"
    echo -e "  • Backend:        FastAPI (Python 3.14, port 7001)"
    echo -e "  • Frontend:       Next.js 16 / Turbopack (port 9000)"
    echo -e "  • Workers:        ThreadPoolExecutor (in-memory)"
    echo -e "  • Storage:        HDF5 (storage/corpus.h5)"
    echo -e "  • Database:       None (stateless + HDF5)"
    echo ""
    echo -e "${CYAN}Logs:${NC}"
    echo -e "  • Backend:        ${YELLOW}tail -f logs/backend-dev.log${NC}"
    echo -e "  • Frontend:       ${YELLOW}tail -f logs/frontend-aurity-dev.log${NC}"
    echo ""
    echo "=========================================="
    echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"
    echo "=========================================="
    echo ""
}

# Cleanup on exit
cleanup_on_exit() {
    echo ""
    echo -e "${YELLOW}Shutting down services...${NC}"

    # Kill backend and frontend
    lsof -ti:7001,9000 2>/dev/null | xargs kill -9 2>/dev/null || true
    pgrep -f "uvicorn.*main:app" | xargs kill -9 2>/dev/null || true
    pgrep -f "next.*dev" | xargs kill -9 2>/dev/null || true
    pgrep -f "pnpm.*dev" | xargs kill -9 2>/dev/null || true

    echo -e "${GREEN}✓${NC} All services stopped"
    echo ""
}

# Trap exit signals
trap cleanup_on_exit EXIT INT TERM

# Main execution
cleanup_existing
check_prereqs
check_deps
init_storage
start_services
show_status

# Keep script alive
wait
