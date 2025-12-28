#!/bin/bash
# Bundle Ollama binary for distribution
#
# Usage:
#   ./bundle-ollama.sh [target]
#
# Targets:
#   aarch64-apple-darwin    - macOS Apple Silicon
#   x86_64-apple-darwin     - macOS Intel
#   x86_64-unknown-linux-gnu - Linux x86_64
#
# This script downloads the appropriate Ollama binary and places it
# in the resources directory for Tauri to bundle.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DESKTOP_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
RESOURCES_DIR="$DESKTOP_ROOT/src-tauri/resources/ollama"

# Ollama version to bundle
OLLAMA_VERSION="0.5.4"

# Determine target
TARGET="${1:-}"
if [ -z "$TARGET" ]; then
    case "$(uname -s)" in
        Darwin*)
            if [[ "$(uname -m)" == "arm64" ]]; then
                TARGET="aarch64-apple-darwin"
            else
                TARGET="x86_64-apple-darwin"
            fi
            ;;
        Linux*)
            TARGET="x86_64-unknown-linux-gnu"
            ;;
        *)
            echo "Usage: $0 <target>"
            echo "Targets: aarch64-apple-darwin, x86_64-apple-darwin, x86_64-unknown-linux-gnu"
            exit 1
            ;;
    esac
fi

echo "=== Bundling Ollama ==="
echo "Version: $OLLAMA_VERSION"
echo "Target: $TARGET"
echo "Output: $RESOURCES_DIR"

# Create resources directory
mkdir -p "$RESOURCES_DIR"

# Determine download URL based on target
case "$TARGET" in
    aarch64-apple-darwin)
        # macOS ARM64 - download the .app bundle and extract
        DOWNLOAD_URL="https://github.com/ollama/ollama/releases/download/v${OLLAMA_VERSION}/Ollama-darwin.zip"
        ARCHIVE_TYPE="zip"
        ;;
    x86_64-apple-darwin)
        DOWNLOAD_URL="https://github.com/ollama/ollama/releases/download/v${OLLAMA_VERSION}/Ollama-darwin.zip"
        ARCHIVE_TYPE="zip"
        ;;
    x86_64-unknown-linux-gnu)
        DOWNLOAD_URL="https://github.com/ollama/ollama/releases/download/v${OLLAMA_VERSION}/ollama-linux-amd64.tgz"
        ARCHIVE_TYPE="tgz"
        ;;
    *)
        echo "Unknown target: $TARGET"
        exit 1
        ;;
esac

echo "Download URL: $DOWNLOAD_URL"

# Download Ollama
TEMP_DIR=$(mktemp -d)
ARCHIVE_FILE="$TEMP_DIR/ollama-archive"

echo "Downloading Ollama..."
curl -L -o "$ARCHIVE_FILE" "$DOWNLOAD_URL"

# Extract based on archive type
echo "Extracting..."
cd "$TEMP_DIR"

case "$ARCHIVE_TYPE" in
    zip)
        unzip -q "$ARCHIVE_FILE"
        # macOS: Extract ollama binary from the .app bundle
        if [ -d "Ollama.app" ]; then
            cp "Ollama.app/Contents/Resources/ollama" "$RESOURCES_DIR/ollama"
        else
            echo "Error: Could not find Ollama.app in archive"
            exit 1
        fi
        ;;
    tgz)
        tar -xzf "$ARCHIVE_FILE"
        if [ -f "ollama" ]; then
            cp "ollama" "$RESOURCES_DIR/ollama"
        elif [ -f "bin/ollama" ]; then
            cp "bin/ollama" "$RESOURCES_DIR/ollama"
        else
            echo "Error: Could not find ollama binary in archive"
            ls -la
            exit 1
        fi
        ;;
esac

# Make executable
chmod +x "$RESOURCES_DIR/ollama"

# Cleanup
rm -rf "$TEMP_DIR"

# Verify
echo ""
echo "=== Ollama Bundled Successfully ==="
echo "Binary: $RESOURCES_DIR/ollama"
ls -lh "$RESOURCES_DIR/ollama"

# Show version
if [ -x "$RESOURCES_DIR/ollama" ]; then
    echo "Version: $("$RESOURCES_DIR/ollama" --version 2>/dev/null || echo 'Unable to verify')"
fi
