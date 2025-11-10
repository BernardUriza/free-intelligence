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
    echo -e "${BLUE}[3/5]${NC} Initializing storage..."

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

# Start Docker services (Full Stack: Redis + Backend + Celery + Flower)
start_docker() {
    echo -e "${BLUE}[4/5]${NC} Starting Docker services..."

    # Check if docker is available
    if ! command -v docker &> /dev/null; then
        echo -e "   ${YELLOW}⚠️  Docker not found - skipping Docker stack${NC}"
        echo ""
        return
    fi

    # Check if docker-compose is available
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null 2>&1; then
        echo -e "   ${YELLOW}⚠️  docker-compose not found - skipping Docker stack${NC}"
        echo ""
        return
    fi

    # Use 'docker compose' (v2) if available, fallback to 'docker-compose' (v1)
    if docker compose version &> /dev/null 2>&1; then
        DOCKER_COMPOSE="docker compose"
    else
        DOCKER_COMPOSE="docker-compose"
    fi

    # Start Full Stack (Redis + Backend + Celery Worker + Flower)
    echo "   Starting Full Docker Stack (Redis + Backend + Workers + Flower)..."
    $DOCKER_COMPOSE -f docker/docker-compose.full.yml up -d --build

    # Wait for services to be healthy
    echo -n "   Waiting for Redis to be healthy"
    for i in {1..30}; do
        if docker inspect fi-redis 2>/dev/null | grep -q '"Status": "healthy"'; then
            echo ""
            echo -e "   ${GREEN}✓${NC} Redis ready"
            break
        fi
        echo -n "."
        sleep 1
    done

    echo -n "   Waiting for Backend API to be healthy"
    for i in {1..30}; do
        if docker inspect fi-backend 2>/dev/null | grep -q '"Status": "healthy"'; then
            echo ""
            echo -e "   ${GREEN}✓${NC} Backend API ready"
            break
        fi
        echo -n "."
        sleep 1
    done

    echo -n "   Waiting for Celery Worker to be healthy"
    for i in {1..30}; do
        if docker inspect fi-celery-worker 2>/dev/null | grep -q '"Status": "healthy"'; then
            echo ""
            echo -e "   ${GREEN}✓${NC} Celery Worker ready"
            break
        fi
        echo -n "."
        sleep 1
    done

    echo -e "   ${GREEN}✓${NC} Flower (monitoring) started"
    echo ""
}

# Cleanup function
cleanup() {
    echo ""
    echo -e "${YELLOW}Shutting down services...${NC}"

    # Kill Frontend process
    if [ -n "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null || true
    fi
    if [ -n "$STRIDE_PID" ]; then
        kill $STRIDE_PID 2>/dev/null || true
    fi

    # Kill any remaining node processes on our ports
    lsof -ti:9000 | xargs kill -9 2>/dev/null || true
    lsof -ti:9050 | xargs kill -9 2>/dev/null || true

    # Stop Docker services (Full Stack)
    if command -v docker &> /dev/null; then
        echo -e "${YELLOW}Stopping Docker stack...${NC}"
        if docker compose version &> /dev/null 2>&1; then
            DOCKER_COMPOSE="docker compose"
        else
            DOCKER_COMPOSE="docker-compose"
        fi
        $DOCKER_COMPOSE -f docker/docker-compose.full.yml down 2>/dev/null || true
        echo -e "${GREEN}✓${NC} Docker stack stopped"
    fi

    echo -e "${GREEN}✓${NC} All services stopped"
    exit 0
}

# Register cleanup handler
trap cleanup SIGINT SIGTERM EXIT

# Start services (Frontend only - Backend runs in Docker)
start_services() {
    echo -e "${BLUE}[5/5]${NC} Starting Frontend service..."
    echo ""

    # Start Frontend (AURITY)
    echo -e "${CYAN}🚀 Starting Frontend AURITY (port 9000)...${NC}"
    cd apps/aurity
    PORT=9000 pnpm dev > ../../logs/frontend-aurity-dev.log 2>&1 &
    FRONTEND_PID=$!
    cd ../..

    # Wait for frontend to be ready (Next.js 16+ can take longer)
    echo -n "   Waiting for frontend to start"
    for i in {1..30}; do
        if curl -s http://localhost:9000 > /dev/null 2>&1; then
            echo ""
            echo -e "   ${GREEN}✓${NC} Frontend AURITY ready"
            break
        fi
        echo -n "."
        sleep 1
    done

    if ! curl -s http://localhost:9000 > /dev/null 2>&1; then
        echo ""
        echo -e "   ${YELLOW}⚠️  Frontend AURITY still starting (Next.js 16 can be slower)...${NC}"
        echo -e "   ${YELLOW}   Check logs: tail -f logs/frontend-aurity-dev.log${NC}"
    fi

    echo ""

    # FI-Stride disabled (commented out for now)
    # echo -e "${CYAN}🚀 Starting Frontend FI-Stride (port 9050)...${NC}"
    # cd apps/fi-stride
    # PORT=9050 pnpm dev > ../../logs/frontend-stride-dev.log 2>&1 &
    # STRIDE_PID=$!
    # cd ../..
    #
    # echo -n "   Waiting for FI-Stride to start"
    # for i in {1..15}; do
    #     if curl -s http://localhost:9050 > /dev/null 2>&1; then
    #         echo ""
    #         echo -e "   ${GREEN}✓${NC} Frontend FI-Stride ready"
    #         break
    #     fi
    #     echo -n "."
    #     sleep 1
    # done
    #
    # if ! curl -s http://localhost:9050 > /dev/null 2>&1; then
    #     echo ""
    #     echo -e "   ${YELLOW}⚠️  Frontend FI-Stride still starting...${NC}"
    #     echo -e "   ${YELLOW}   Check logs: tail -f logs/frontend-stride-dev.log${NC}"
    # fi

    echo -e "   ${YELLOW}ℹ️  FI-Stride disabled (not started)${NC}"
    echo ""
}

# Display info
show_info() {
    echo "=========================================="
    echo -e "${GREEN}✅ All Services Running${NC}"
    echo "=========================================="
    echo ""
    echo -e "${CYAN}Services:${NC}"
    echo "  • Backend API (Docker):  http://localhost:7001"
    echo "    └─ Docs:               http://localhost:7001/docs"
    echo "    └─ Health:             http://localhost:7001/health"
    echo ""
    echo "  • AURITY Frontend (Host): http://localhost:9000"
    echo "    └─ Dashboard:           http://localhost:9000/dashboard"
    echo "    └─ Triage:              http://localhost:9000/triage"
    echo ""

    # Show Docker services
    if command -v docker &> /dev/null && docker ps --format '{{.Names}}' | grep -q "fi-redis"; then
        echo -e "${CYAN}Docker Stack:${NC}"
        echo "  • Redis:           localhost:6379 (broker)"
        echo "  • Backend API:     localhost:7001 (Docker)"
        echo "  • Celery Worker:   2 workers (queues: asr, celery)"
        echo "  • Flower:          http://localhost:5555 (monitoring)"
        echo ""
    fi

    echo -e "  ${YELLOW}• FI-Stride SPA: DISABLED${NC}"
    echo ""
    echo -e "${CYAN}Logs:${NC}"
    echo "  • Backend (Docker):  docker logs -f fi-backend"
    echo "  • AURITY (Host):     tail -f logs/frontend-aurity-dev.log"
    echo "  • Celery Worker:     docker logs -f fi-celery-worker"
    echo "  • All Docker:        docker compose -f docker/docker-compose.full.yml logs -f"
    echo ""
    echo -e "${CYAN}Process IDs:${NC}"
    echo "  • AURITY PID:     $FRONTEND_PID"
    echo ""
    echo "=========================================="
    echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"
    echo "=========================================="
    echo ""
    echo -e "${CYAN}Stack:${NC}"
    echo "  • Backend API:         FastAPI (Docker, port 7001)"
    echo "  • Frontend:            Next.js 16.0.1 (Host, port 9000)"
    echo "  • Infrastructure:      Redis 7 + Celery 5.5 + Flower 2.0 (Docker)"
    echo "  • ASR Engine:          faster-whisper small INT8 (Docker Worker)"
    echo ""
    echo -e "${GREEN}✨ Full Docker deployment active!${NC}"
    echo ""
    echo -e "${YELLOW}Note: FI-Stride disabled. To run it separately: make stride-dev${NC}"
    echo ""
}

# Monitor logs in real-time
monitor_logs() {
    # Use tail to follow all logs (FI-Stride disabled)
    tail -f logs/backend-dev.log logs/frontend-aurity-dev.log 2>/dev/null || {
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
    start_docker
    start_services
    show_info
    monitor_logs
}

main
