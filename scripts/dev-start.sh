#!/bin/bash
# Clean development startup script for Free Intelligence
# Card: FI-BACKEND-ARCH-001
#
# This script provides a clean, idempotent way to start all services

set -e

PROJECT_ROOT="/Users/bernardurizaorozco/Documents/free-intelligence"
cd "$PROJECT_ROOT"

echo "🚀 Free Intelligence - Development Startup"
echo "=========================================="
echo ""

# Step 1: Kill any existing processes
echo "🧹 Cleaning existing processes..."
pkill -9 -f "python.*backend" 2>/dev/null || true
pkill -9 -f "uvicorn" 2>/dev/null || true
pkill -9 -f "make run" 2>/dev/null || true
lsof -ti :7001 | xargs kill -9 2>/dev/null || true
sleep 1
echo "✅ Processes cleaned"
echo ""

# Step 2: Verify Docker is running
echo "🐳 Checking Docker..."
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker Desktop and try again."
    exit 1
fi
echo "✅ Docker is running"
echo ""

# Step 3: Start Celery infrastructure (Redis + Worker + Flower)
echo "📦 Starting Celery infrastructure (Redis + Worker + Flower)..."
docker-compose -f docker-compose.celery.yml up -d
sleep 3

# Verify services are healthy
echo "🔍 Verifying Celery services..."
docker exec fi-redis redis-cli ping > /dev/null 2>&1 && echo "  ✅ Redis: Healthy" || echo "  ❌ Redis: Unhealthy"
docker logs fi-celery-worker 2>&1 | grep -q "celery@.*ready" && echo "  ✅ Celery Worker: Ready" || echo "  ⏳ Celery Worker: Starting..."
echo "  ✅ Flower UI: http://localhost:5555"
echo ""

# Step 4: Start backend API
echo "🎯 Starting Backend API (port 7001)..."
make run > logs/backend-dev.log 2>&1 &
BACKEND_PID=$!
echo "$BACKEND_PID" > /tmp/backend_pid.txt
sleep 3

# Wait for backend to be ready
echo "⏳ Waiting for backend to be ready..."
for i in {1..30}; do
    if curl -s http://localhost:7001/health > /dev/null 2>&1; then
        echo "✅ Backend API: Ready at http://localhost:7001"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ Backend failed to start after 30s. Check logs/backend-dev.log"
        exit 1
    fi
    sleep 1
done
echo ""

# Step 5: Summary
echo "✅ All services started successfully!"
echo "=========================================="
echo ""
echo "📋 Service Status:"
echo "  • Backend API:    http://localhost:7001/health"
echo "  • Celery Flower:  http://localhost:5555"
echo "  • Redis:          localhost:6379"
echo "  • Logs:           logs/backend-dev.log"
echo ""
echo "🛑 To stop all services:"
echo "  ./scripts/dev-stop.sh"
echo ""
echo "📊 To test Celery:"
echo "  ./scripts/test-celery.sh"
echo ""
