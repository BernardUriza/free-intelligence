#!/bin/bash
# =============================================================================
# Aurity Desktop - Linux Build Script for Digital Ocean
# =============================================================================
#
# This script runs on DO to build the Linux version of Aurity Desktop.
# macOS builds must be done locally on a Mac and uploaded.
#
# Usage:
#   ./build-desktop-linux.sh [version]
#
# Example:
#   ./build-desktop-linux.sh 1.0.0
#
# Output:
#   /opt/aurity/releases/Aurity-<version>-linux.AppImage
#
# =============================================================================

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DESKTOP_ROOT="$PROJECT_ROOT/apps/aurity-desktop"
RELEASES_DIR="/opt/aurity/releases"

VERSION="${1:-$(date +%Y.%m.%d)}"

echo "=============================================="
echo "  Aurity Desktop Linux Build"
echo "=============================================="
echo "  Version: $VERSION"
echo "  Project: $PROJECT_ROOT"
echo "  Output:  $RELEASES_DIR"
echo "=============================================="

# Check if running on Linux
if [ "$(uname -s)" != "Linux" ]; then
    echo "ERROR: This script must run on Linux (Digital Ocean)"
    echo "       For macOS builds, use: ./build-desktop-macos.sh"
    exit 1
fi

# Create releases directory
mkdir -p "$RELEASES_DIR"

# Step 1: Install system dependencies (first time only)
echo ""
echo "[1/5] Checking system dependencies..."
if ! command -v cargo &> /dev/null; then
    echo "Installing Rust..."
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
    source "$HOME/.cargo/env"
fi

# Tauri dependencies for Linux
if ! dpkg -s libwebkit2gtk-4.1-dev &> /dev/null; then
    echo "Installing Tauri Linux dependencies..."
    sudo apt-get update
    sudo apt-get install -y \
        libwebkit2gtk-4.1-dev \
        build-essential \
        curl \
        wget \
        file \
        libxdo-dev \
        libssl-dev \
        libayatana-appindicator3-dev \
        librsvg2-dev
fi

# Step 2: Build Python backend sidecar
echo ""
echo "[2/5] Building Python backend sidecar..."
cd "$DESKTOP_ROOT/pyinstaller"
./build.sh

# Step 3: Install Node.js dependencies
echo ""
echo "[3/5] Installing Node.js dependencies..."
cd "$PROJECT_ROOT"
pnpm install --frozen-lockfile

# Step 4: Build the Tauri app
echo ""
echo "[4/5] Building Tauri app..."
cd "$DESKTOP_ROOT"
pnpm build

# Step 5: Copy release artifact
echo ""
echo "[5/5] Copying release artifact..."
APPIMAGE=$(find "$DESKTOP_ROOT/src-tauri/target/release/bundle/appimage" -name "*.AppImage" 2>/dev/null | head -1)

if [ -z "$APPIMAGE" ]; then
    echo "ERROR: AppImage not found"
    echo "Looking in: $DESKTOP_ROOT/src-tauri/target/release/bundle/"
    ls -la "$DESKTOP_ROOT/src-tauri/target/release/bundle/" 2>/dev/null || echo "Bundle directory not found"
    exit 1
fi

OUTPUT_FILE="$RELEASES_DIR/Aurity-${VERSION}-linux.AppImage"
cp "$APPIMAGE" "$OUTPUT_FILE"
chmod +x "$OUTPUT_FILE"

# Generate checksum
sha256sum "$OUTPUT_FILE" > "$OUTPUT_FILE.sha256"

echo ""
echo "=============================================="
echo "  BUILD COMPLETE"
echo "=============================================="
echo "  Artifact: $OUTPUT_FILE"
echo "  Size:     $(du -h "$OUTPUT_FILE" | cut -f1)"
echo "  SHA256:   $(cat "$OUTPUT_FILE.sha256" | cut -d' ' -f1)"
echo "=============================================="
echo ""
echo "To upload macOS build, use:"
echo "  scp Aurity-${VERSION}-macos.dmg root@104.131.175.65:$RELEASES_DIR/"
echo ""
