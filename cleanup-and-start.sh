#!/bin/bash
set -e

echo "🔨 Killing all processes on ports 7001 and 9000..."
lsof -ti:7001,9000 2>/dev/null | xargs kill -9 2>/dev/null || true

echo "🔨 Killing all uvicorn, node, pnpm, python processes..."
pkill -9 -f "uvicorn" 2>/dev/null || true
pkill -9 -f "next dev" 2>/dev/null || true
pkill -9 -f "pnpm" 2>/dev/null || true
pkill -9 -f "python.*uvicorn" 2>/dev/null || true

echo "⏳ Waiting for ports to be released..."
sleep 4

echo "✅ Cleanup complete. Starting services with make dev-all..."
make dev-all
