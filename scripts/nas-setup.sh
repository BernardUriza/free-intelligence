#!/bin/bash
# Free Intelligence - NAS Setup Script
# Quick installation for Synology/QNAP/TrueNAS
#
# Usage: ./scripts/nas-setup.sh

set -e

echo "=========================================="
echo "Free Intelligence - NAS Setup"
echo "=========================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

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
    echo "[INFO] $1"
}

# 1. Check prerequisites
info "Checking prerequisites..."

# Check Node.js
if ! command -v node &> /dev/null; then
    error "Node.js not found. Please install Node.js 18+ first."
fi
NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 18 ]; then
    error "Node.js 18+ required. Current: v$NODE_VERSION"
fi
success "Node.js $(node -v) detected"

# Check Python
if ! command -v python3 &> /dev/null; then
    error "Python3 not found. Please install Python 3.11+ first."
fi
PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
success "Python $(python3 --version) detected"

# Check pnpm
if ! command -v pnpm &> /dev/null; then
    warning "pnpm not found. Installing globally..."
    npm install -g pnpm@8.15.0
    success "pnpm installed"
else
    success "pnpm $(pnpm -v) detected"
fi

# 2. Create necessary directories
info "Creating directory structure..."
mkdir -p storage
mkdir -p backups
mkdir -p logs
mkdir -p config
success "Directories created"

# 3. Install Node.js dependencies
info "Installing Node.js dependencies (this may take a few minutes)..."
pnpm install --frozen-lockfile || error "Failed to install Node.js dependencies"
success "Node.js dependencies installed"

# 4. Install Python dependencies
info "Setting up Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv || error "Failed to create virtual environment"
fi
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt || error "Failed to install Python dependencies"
success "Python dependencies installed"

# 5. Setup environment file
if [ ! -f ".env.local" ]; then
    info "Creating .env.local from template..."
    if [ -f ".env.example" ]; then
        cp .env.example .env.local
        warning "Please edit .env.local with your NAS-specific configuration"
    else
        cat > .env.local << 'EOF'
# Free Intelligence - NAS Configuration
# Edit these values for your environment

# Storage paths (adjust for your NAS)
CORPUS_PATH=./storage/corpus.h5
BACKUP_PATH=./backups

# API endpoints (LAN-only - replace with your NAS IP)
NEXT_PUBLIC_API_URL=http://192.168.1.100:9001
TIMELINE_API_URL=http://192.168.1.100:9002

# Port configuration
PORT=9000
API_PORT=9001
TIMELINE_PORT=9002

# Node environment
NODE_ENV=production
NEXT_TELEMETRY_DISABLED=1
EOF
        success ".env.local created (PLEASE EDIT WITH YOUR NAS IP)"
    fi
else
    success ".env.local already exists"
fi

# 6. Build production assets
info "Building production assets with Turborepo..."
pnpm build || error "Build failed"
success "Production build complete"

# 7. Initialize corpus (if needed)
if [ ! -f "storage/corpus.h5" ]; then
    info "Initializing empty corpus..."
    python3 scripts/init_corpus.py || warning "Corpus initialization skipped (script not found)"
fi

# 8. Set permissions
info "Setting file permissions..."
chmod +x scripts/*.sh
chmod 755 storage backups logs
success "Permissions set"

# 9. Summary
echo ""
echo "=========================================="
echo -e "${GREEN}Setup Complete!${NC}"
echo "=========================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Edit .env.local with your NAS IP address:"
echo "   nano .env.local"
echo ""
echo "2. Start services manually:"
echo "   # Terminal 1: Backend API"
echo "   make run"
echo ""
echo "   # Terminal 2: Timeline API"
echo "   make run-timeline"
echo ""
echo "   # Terminal 3: Frontend"
echo "   cd apps/aurity && pnpm start"
echo ""
echo "OR use PM2 (recommended):"
echo "   npm install -g pm2"
echo "   pm2 start ecosystem.config.js"
echo "   pm2 save"
echo ""
echo "Access the application:"
echo "   Frontend: http://your-nas-ip:9000"
echo "   Backend:  http://your-nas-ip:9001/docs"
echo "   Timeline: http://your-nas-ip:9002/docs"
echo ""
echo "Documentation: ./NAS_DEPLOYMENT.md"
echo "=========================================="
