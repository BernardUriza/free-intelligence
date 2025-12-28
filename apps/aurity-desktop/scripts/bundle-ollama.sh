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
#
# SECURITY: All downloads are verified using SHA256 checksums from
# official Ollama GitHub releases.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DESKTOP_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
RESOURCES_DIR="$DESKTOP_ROOT/src-tauri/resources/ollama"

# Ollama version to bundle
OLLAMA_VERSION="0.5.4"

# SHA256 checksums for Ollama v0.5.4 releases
# Obtained from: https://github.com/ollama/ollama/releases/tag/v0.5.4
# To update: download checksums.txt from the release page
declare -A CHECKSUMS
CHECKSUMS["darwin"]="49e64ac13ec508f6ca03a4248e6f3df16f41a8cd4dd47a2fb91ec50d9f7db09c"
CHECKSUMS["linux-amd64"]="ffbd3f52091e88f89c280010d70c94e6fdbfbecfce7e1c59f97a1c7b1ccf74d6"

# Function to verify SHA256 checksum
verify_checksum() {
    local file="$1"
    local expected="$2"

    if [ -z "$expected" ]; then
        echo "ERROR: No checksum available for this target"
        echo "SECURITY: Refusing to bundle unverified binary"
        echo "Please update the CHECKSUMS array with the official checksum"
        exit 1
    fi

    echo "Verifying SHA256 checksum..."
    local actual
    if command -v sha256sum &> /dev/null; then
        actual=$(sha256sum "$file" | cut -d' ' -f1)
    elif command -v shasum &> /dev/null; then
        actual=$(shasum -a 256 "$file" | cut -d' ' -f1)
    else
        echo "ERROR: No SHA256 tool available (need sha256sum or shasum)"
        exit 1
    fi

    if [ "$actual" != "$expected" ]; then
        echo "ERROR: Checksum verification FAILED!"
        echo "  Expected: $expected"
        echo "  Actual:   $actual"
        echo "SECURITY: The downloaded file may have been tampered with"
        echo "Please verify you're downloading from official sources"
        rm -f "$file"
        exit 1
    fi

    echo "Checksum verified: $actual"
}

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

# Determine download URL and checksum based on target
case "$TARGET" in
    aarch64-apple-darwin)
        # macOS ARM64 - download the .app bundle and extract
        DOWNLOAD_URL="https://github.com/ollama/ollama/releases/download/v${OLLAMA_VERSION}/Ollama-darwin.zip"
        ARCHIVE_TYPE="zip"
        EXPECTED_CHECKSUM="${CHECKSUMS[darwin]}"
        ;;
    x86_64-apple-darwin)
        DOWNLOAD_URL="https://github.com/ollama/ollama/releases/download/v${OLLAMA_VERSION}/Ollama-darwin.zip"
        ARCHIVE_TYPE="zip"
        EXPECTED_CHECKSUM="${CHECKSUMS[darwin]}"
        ;;
    x86_64-unknown-linux-gnu)
        DOWNLOAD_URL="https://github.com/ollama/ollama/releases/download/v${OLLAMA_VERSION}/ollama-linux-amd64.tgz"
        ARCHIVE_TYPE="tgz"
        EXPECTED_CHECKSUM="${CHECKSUMS[linux-amd64]}"
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

# SECURITY: Verify integrity before extraction
verify_checksum "$ARCHIVE_FILE" "$EXPECTED_CHECKSUM"

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
