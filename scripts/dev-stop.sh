#!/bin/bash
# Stop all Free Intelligence development services
# Card: FI-BACKEND-ARCH-001

set -e

PROJECT_ROOT="/Users/bernardurizaorozco/Documents/free-intelligence"
cd "$PROJECT_ROOT"

echo "🛑 Stopping Free Intelligence Services"
echo "======================================="
echo ""

# Stop backend API
echo "🛑 Stopping Backend API..."
if [ -f /tmp/backend_pid.txt ]; then
    BACKEND_PID=$(cat /tmp/backend_pid.txt)
    kill -9 "$BACKEND_PID" 2>/dev/null || true
    rm /tmp/backend_pid.txt
fi
pkill -9 -f "python.*backend" 2>/dev/null || true
pkill -9 -f "uvicorn" 2>/dev/null || true
lsof -ti :7001 | xargs kill -9 2>/dev/null || true
echo "✅ Backend stopped"
echo ""

# Stop Celery infrastructure
echo "🛑 Stopping Celery infrastructure..."
docker-compose -f docker/docker-compose.celery.yml down
echo "✅ Celery infrastructure stopped"
echo ""

echo "✅ All services stopped successfully!"
