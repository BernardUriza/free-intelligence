#!/bin/bash
# Nuclear cleanup script for Free Intelligence
# Kills ALL backend/frontend processes and clears ports
# Author: Bernard Uriza Orozco
# Date: 2025-11-14

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${RED}   🔥 NUCLEAR CLEANUP - FREE INTELLIGENCE 🔥${NC}"
echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Function to kill processes on a specific port
kill_port() {
    local port=$1
    local name=$2
    echo -e "${YELLOW}[PORT $port]${NC} Checking for $name processes..."

    pids=$(lsof -ti:$port 2>/dev/null || true)
    if [ -n "$pids" ]; then
        echo -e "${YELLOW}  └─ Found PIDs: $pids${NC}"
        echo "$pids" | xargs kill -9 2>/dev/null || true
        echo -e "${GREEN}  └─ ✓ Killed${NC}"
    else
        echo -e "${GREEN}  └─ ✓ Port clean${NC}"
    fi
}

# Function to kill processes by name pattern
kill_pattern() {
    local pattern=$1
    local name=$2
    echo -e "${YELLOW}[$name]${NC} Killing processes matching '$pattern'..."

    pids=$(pgrep -f "$pattern" 2>/dev/null || true)
    if [ -n "$pids" ]; then
        echo -e "${YELLOW}  └─ Found PIDs: $pids${NC}"
        echo "$pids" | xargs kill -9 2>/dev/null || true
        echo -e "${GREEN}  └─ ✓ Killed${NC}"
    else
        echo -e "${GREEN}  └─ ✓ No processes found${NC}"
    fi
}

echo -e "${YELLOW}Step 1: Killing port-based processes${NC}"
kill_port 7001 "Backend API"
kill_port 9000 "Frontend (Aurity)"
kill_port 9050 "PWA (KATNISS)"
kill_port 11434 "Ollama"
echo ""

echo -e "${YELLOW}Step 2: Killing backend processes${NC}"
kill_pattern "uvicorn.*main:app" "Uvicorn (Backend)"
kill_pattern "python.*backend/app/main.py" "Backend Main"
kill_pattern "celery.*worker" "Celery Workers"
echo ""

echo -e "${YELLOW}Step 3: Killing frontend processes${NC}"
kill_pattern "next.*dev.*-p 9000" "Next.js Dev Server (Aurity)"
kill_pattern "next-server.*v16" "Next.js Server"
kill_pattern "postcss.js" "PostCSS Workers"
kill_pattern "pnpm.*dev" "pnpm dev"
echo ""

echo -e "${YELLOW}Step 4: Killing orphaned node processes${NC}"
# Only kill node processes in free-intelligence directory
pids=$(ps aux | grep node | grep free-intelligence | grep -v grep | awk '{print $2}' || true)
if [ -n "$pids" ]; then
    echo -e "${YELLOW}  └─ Found orphaned node PIDs: $pids${NC}"
    echo "$pids" | xargs kill -9 2>/dev/null || true
    echo -e "${GREEN}  └─ ✓ Killed${NC}"
else
    echo -e "${GREEN}  └─ ✓ No orphaned processes${NC}"
fi
echo ""

echo -e "${YELLOW}Step 5: Final verification${NC}"
echo "Remaining processes on critical ports:"
lsof -ti:7001,9000,9050,11434 2>/dev/null || echo -e "${GREEN}  └─ ✓ All ports clean${NC}"
echo ""

echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}   ✓ CLEANUP COMPLETE${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "You can now run: make dev-all"
