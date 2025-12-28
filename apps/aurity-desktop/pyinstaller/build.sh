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

# Check for PyInstaller
if ! command -v pyinstaller &> /dev/null; then
    echo "Installing PyInstaller..."
    pip3 install pyinstaller
fi

# Install backend dependencies if needed
echo "Checking backend dependencies..."
cd "$BACKEND_ROOT"
if [ -f "requirements-prod.txt" ]; then
    pip3 install -r requirements-prod.txt -q
else
    echo "WARNING: requirements-prod.txt not found, using requirements.txt"
    pip3 install -r requirements.txt -q
fi

# Run PyInstaller
echo "Running PyInstaller..."
cd "$SCRIPT_DIR"
pyinstaller --clean --noconfirm aurity-backend.spec

# Create Tauri binaries directory
BINARIES_DIR="$DESKTOP_ROOT/src-tauri/binaries"
mkdir -p "$BINARIES_DIR"

# Copy the built binary with platform suffix
echo "Copying binary to Tauri binaries directory..."
cp -r "$SCRIPT_DIR/dist/aurity-backend" "$BINARIES_DIR/aurity-backend$BINARY_SUFFIX"

# Make executable
chmod +x "$BINARIES_DIR/aurity-backend$BINARY_SUFFIX"

echo ""
echo "=== Build Complete ==="
echo "Binary: $BINARIES_DIR/aurity-backend$BINARY_SUFFIX"
echo ""
echo "Next steps:"
echo "  1. cd $DESKTOP_ROOT"
echo "  2. pnpm install"
echo "  3. pnpm dev    # For development"
echo "  4. pnpm build  # For production"
