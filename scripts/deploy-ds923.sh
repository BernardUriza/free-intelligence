#!/bin/bash
# Free Intelligence - DS923+ Deployment Script
# Deploys Ollama + ASR workers on Synology NAS
#
# Prerequisites:
#   - Docker installed on DS923+
#   - /volume1/ollama directory exists
#   - /volume1/fi directory structure created
#
# Usage: ./scripts/deploy-ds923.sh

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo ""
echo "=========================================="
echo -e "${CYAN}Free Intelligence - DS923+ Deployment${NC}"
echo "=========================================="
echo ""

# Helper functions
error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

# Check if running with Docker access
if ! docker ps > /dev/null 2>&1; then
    error "Docker not accessible. Please run with Docker privileges."
fi

success "Docker accessible"

# 1. Create directory structure
info "Creating directory structure..."

VOLUME_BASE="/volume1/fi"
OLLAMA_DIR="/volume1/ollama"

mkdir -p "$VOLUME_BASE/ready"
mkdir -p "$VOLUME_BASE/asr/json"
mkdir -p "$VOLUME_BASE/asr/logs"
mkdir -p "$OLLAMA_DIR"

success "Directories created:
  - $VOLUME_BASE/ready (audio input)
  - $VOLUME_BASE/asr/json (transcription output)
  - $OLLAMA_DIR (Ollama models)"

# 2. Deploy Ollama
echo ""
info "Deploying Ollama service..."

docker compose -f docker-compose.ollama.yml down 2>/dev/null || true
docker compose -f docker-compose.ollama.yml up -d

# Wait for Ollama to be ready
echo -n "Waiting for Ollama to start"
for i in {1..30}; do
    if curl -sf http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo ""
        success "Ollama is ready"
        break
    fi
    echo -n "."
    sleep 2
done

if ! curl -sf http://localhost:11434/api/tags > /dev/null 2>&1; then
    warning "Ollama may still be starting... continuing anyway"
fi

# 3. Pull LLM models
echo ""
info "Pulling LLM models (this may take several minutes)..."

MODELS=(
    "qwen2:7b-instruct"
    "deepseek-r1:7b"
)

for model in "${MODELS[@]}"; do
    info "Pulling $model..."
    docker exec fi-ollama ollama pull "$model" || warning "Failed to pull $model"
done

success "Models pulled"

# 4. Deploy ASR worker
echo ""
info "Deploying ASR worker..."

docker compose -f docker-compose.asr.yml down 2>/dev/null || true
docker compose -f docker-compose.asr.yml up -d

sleep 5

if docker ps --filter "name=fi-asr-worker" --format "{{.Names}}" | grep -q "fi-asr-worker"; then
    success "ASR worker deployed"
else
    warning "ASR worker may have issues, check logs: docker logs fi-asr-worker"
fi

# 5. Verify deployment
echo ""
info "Verifying deployment..."

# Check Ollama
if curl -sf http://localhost:11434/api/tags > /dev/null 2>&1; then
    success "Ollama API responding (http://localhost:11434)"
else
    error "Ollama API not responding"
fi

# Check ASR worker
if [ -f "/tmp/worker.pid" ]; then
    success "ASR worker PID file exists"
else
    warning "ASR worker PID file not found"
fi

# 6. Smoke tests
echo ""
info "Running smoke tests..."

# Test Ollama generate
info "Testing Ollama generation..."
RESPONSE=$(curl -s http://localhost:11434/api/generate \
    -d '{"model":"qwen2:7b-instruct","prompt":"Di hola en español.","stream":false}' \
    | head -1)

if echo "$RESPONSE" | grep -q "response"; then
    success "Ollama generate working"
else
    warning "Ollama generate may have issues"
fi

# 7. Display status
echo ""
echo "=========================================="
echo -e "${GREEN}Deployment Complete${NC}"
echo "=========================================="
echo ""
echo -e "${CYAN}Services:${NC}"
echo "  • Ollama API:  http://localhost:11434"
echo "  • ASR Worker:  Monitoring $VOLUME_BASE/ready"
echo ""
echo -e "${CYAN}Docker Containers:${NC}"
docker ps --filter "name=fi-" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""
echo -e "${CYAN}Ollama Models:${NC}"
docker exec fi-ollama ollama list 2>/dev/null || echo "  (Unable to list models)"
echo ""
echo -e "${CYAN}Directory Structure:${NC}"
echo "  Input:  $VOLUME_BASE/ready/*.{wav,mp3,m4a}"
echo "  Output: $VOLUME_BASE/asr/json/*.json"
echo "  Logs:   $VOLUME_BASE/asr/logs/worker.log"
echo ""
echo -e "${CYAN}Monitoring:${NC}"
echo "  docker logs -f fi-ollama"
echo "  docker logs -f fi-asr-worker"
echo "  tail -f $VOLUME_BASE/asr/logs/worker.log"
echo ""
echo -e "${CYAN}Testing:${NC}"
echo "  # Test Ollama"
echo "  curl -s http://localhost:11434/api/generate \\"
echo "    -d '{\"model\":\"qwen2:7b-instruct\",\"prompt\":\"Hola\"}' | head"
echo ""
echo "  # Test ASR (place audio file)"
echo "  cp sample.wav $VOLUME_BASE/ready/"
echo "  # Wait ~30s, check output"
echo "  ls -lh $VOLUME_BASE/asr/json/"
echo ""
echo "=========================================="
