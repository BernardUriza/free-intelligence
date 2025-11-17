#!/bin/bash
# Free Intelligence - Development Process Monitor
# Watches for zombie processes and stale code
# Author: Bernard Uriza Orozco
# Date: 2025-11-14

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}   🔍 FREE INTELLIGENCE - DEV MONITOR${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Function to check if a process is responding
check_health() {
    local port=$1
    local name=$2
    local endpoint=$3

    if ! lsof -ti:$port > /dev/null 2>&1; then
        echo -e "${RED}[$name]${NC} ❌ NO PROCESS on port $port"
        return 1
    fi

    if ! curl -s -m 5 "http://localhost:$port$endpoint" > /dev/null 2>&1; then
        echo -e "${YELLOW}[$name]${NC} ⚠️  Process running but NOT responding on port $port"
        return 1
    fi

    echo -e "${GREEN}[$name]${NC} ✓ Healthy (port $port)"
    return 0
}

# Function to check file modification time vs process start time
check_code_staleness() {
    local port=$1
    local watch_dir=$2
    local name=$3

    # Get PID of process on port
    pid=$(lsof -ti:$port 2>/dev/null || echo "")
    if [ -z "$pid" ]; then
        return 1
    fi

    # Get process start time (macOS compatible)
    process_start=$(ps -p $pid -o lstart= 2>/dev/null | xargs -I {} date -j -f "%a %b %d %H:%M:%S %Y" "{}" +%s 2>/dev/null || echo "0")

    # Find most recently modified Python/JS file in watch directory
    if [ "$watch_dir" = "backend" ]; then
        newest_file=$(find backend -name "*.py" -type f -not -path "*/.*" -exec stat -f "%m %N" {} \; 2>/dev/null | sort -rn | head -1 || echo "0")
    else
        newest_file=$(find apps/aurity -name "*.ts" -o -name "*.tsx" -o -name "*.js" -type f -not -path "*/node_modules/*" -not -path "*/.next/*" -exec stat -f "%m %N" {} \; 2>/dev/null | sort -rn | head -1 || echo "0")
    fi

    file_mtime=$(echo "$newest_file" | awk '{print $1}')

    if [ "$file_mtime" -gt "$process_start" ]; then
        file_name=$(echo "$newest_file" | cut -d' ' -f2-)
        echo -e "${RED}[$name]${NC} ⚠️  STALE CODE DETECTED!"
        echo -e "${RED}  └─ Process started: $(date -r $process_start +'%Y-%m-%d %H:%M:%S')${NC}"
        echo -e "${RED}  └─ Code modified:   $(date -r $file_mtime +'%Y-%m-%d %H:%M:%S')${NC}"
        echo -e "${RED}  └─ File: $file_name${NC}"
        echo -e "${YELLOW}  └─ ACTION: Restart required (make dev-restart)${NC}"
        return 1
    fi

    return 0
}

# Main monitoring loop
echo -e "${CYAN}Starting continuous monitoring (Ctrl+C to stop)...${NC}"
echo ""

iteration=0
while true; do
    iteration=$((iteration + 1))
    echo -e "${CYAN}[$(date +'%H:%M:%S')] Iteration #$iteration${NC}"
    echo ""

    # Check Backend (Docker or Native)
    if docker ps --format '{{.Names}}' | grep -q "fi-backend" 2>/dev/null; then
        # Docker mode
        if docker inspect fi-backend 2>/dev/null | grep -q '"Status": "healthy"'; then
            echo -e "${GREEN}[Backend]${NC} ✓ Healthy (Docker)"
        else
            echo -e "${YELLOW}[Backend]${NC} ⚠️  Docker container unhealthy"
        fi
    else
        # Native mode
        check_health 7001 "Backend" "/health"
        check_code_staleness 7001 "backend" "Backend"
    fi

    # Check Frontend
    check_health 9000 "Frontend" "/"
    check_code_staleness 9000 "apps/aurity" "Frontend"

    echo ""
    echo -e "${CYAN}Next check in 30 seconds...${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    sleep 30
done
