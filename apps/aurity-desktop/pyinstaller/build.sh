#!/bin/bash
# Build script for Aurity Backend sidecar
#
# This script:
# 1. Creates a virtual environment with minimal dependencies
# 2. Runs PyInstaller to create the standalone executable
# 3. Copies the result to the Tauri binaries directory

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
DESKTOP_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_ROOT="$PROJECT_ROOT/backend"

echo "=== Aurity Backend Build ==="
echo "Project root: $PROJECT_ROOT"
echo "Desktop root: $DESKTOP_ROOT"
echo "Backend root: $BACKEND_ROOT"

# Security: Mock auth requires explicit opt-in via environment variable
# This prevents accidental builds with authentication bypass
if [ ! -f "$DESKTOP_ROOT/.env.desktop" ]; then
    if [ -f "$DESKTOP_ROOT/.env.desktop.example" ]; then
        if [ "${ENABLE_DESKTOP_MOCK_AUTH:-0}" = "1" ]; then
            echo "Creating .env.desktop with mock auth ENABLED (ENABLE_DESKTOP_MOCK_AUTH=1)"
            echo "WARNING: This build will bypass authentication - only use for offline desktop"
            sed 's/NEXT_PUBLIC_USE_MOCK_AUTH=false/NEXT_PUBLIC_USE_MOCK_AUTH=true/' \
                "$DESKTOP_ROOT/.env.desktop.example" > "$DESKTOP_ROOT/.env.desktop"
        else
            echo "Creating .env.desktop with SECURE defaults (mock auth disabled)"
            echo "To enable mock auth for offline desktop, set: ENABLE_DESKTOP_MOCK_AUTH=1"
            cp "$DESKTOP_ROOT/.env.desktop.example" "$DESKTOP_ROOT/.env.desktop"
        fi
    else
        echo "WARNING: .env.desktop.example not found, skipping env setup"
    fi
fi

# Determine platform-specific binary name
case "$(uname -s)" in
    Darwin*)
        if [[ "$(uname -m)" == "arm64" ]]; then
            BINARY_SUFFIX="-aarch64-apple-darwin"
        else
            BINARY_SUFFIX="-x86_64-apple-darwin"
        fi
        ;;
    Linux*)
        BINARY_SUFFIX="-x86_64-unknown-linux-gnu"
        ;;
    *)
        echo "Unsupported platform: $(uname -s)"
        exit 1
        ;;
esac

echo "Binary suffix: $BINARY_SUFFIX"

# Create isolated virtual environment for build (prevents system contamination)
VENV_DIR="$SCRIPT_DIR/.venv-build"
echo "Setting up isolated build environment..."

if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment: $VENV_DIR"
    python3 -m venv "$VENV_DIR"
fi

# Activate virtual environment
source "$VENV_DIR/bin/activate"
echo "Using Python: $(which python3)"

# Install PyInstaller in venv
echo "Installing PyInstaller in virtual environment..."
pip install --upgrade pip -q
pip install pyinstaller -q

# Install backend dependencies in venv
echo "Installing backend dependencies in virtual environment..."
cd "$BACKEND_ROOT"
if [ -f "requirements-prod.txt" ]; then
    pip install -r requirements-prod.txt -q
else
    echo "WARNING: requirements-prod.txt not found, using requirements.txt"
    pip install -r requirements.txt -q
fi

# Run PyInstaller (now using venv's pyinstaller)
echo "Running PyInstaller..."
cd "$SCRIPT_DIR"
python -m PyInstaller --clean --noconfirm aurity-backend.spec

# Create Tauri binaries directory
BINARIES_DIR="$DESKTOP_ROOT/src-tauri/binaries"
mkdir -p "$BINARIES_DIR"

# Copy the built binary with platform suffix
echo "Copying binary to Tauri binaries directory..."
cp -r "$SCRIPT_DIR/dist/aurity-backend" "$BINARIES_DIR/aurity-backend$BINARY_SUFFIX"

# Make executable
chmod +x "$BINARIES_DIR/aurity-backend$BINARY_SUFFIX"

# Deactivate virtual environment
deactivate 2>/dev/null || true

echo ""
echo "=== Build Complete ==="
echo "Binary: $BINARIES_DIR/aurity-backend$BINARY_SUFFIX"
echo ""
echo "Build environment: $VENV_DIR (isolated, can be deleted)"
echo ""
echo "Next steps:"
echo "  1. cd $DESKTOP_ROOT"
echo "  2. pnpm install"
echo "  3. pnpm dev    # For development"
echo "  4. pnpm build  # For production"
