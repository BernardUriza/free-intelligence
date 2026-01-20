#!/bin/bash
set -e

PYTHON_VERSION="3.14.0"
ARCH="amd64"
PYTHON_URL="https://www.python.org/ftp/python/${PYTHON_VERSION}/python-${PYTHON_VERSION}-amd64.exe"
OUTPUT_DIR="$(dirname "$0")/../resources/python-installer"

echo "=== Preparing Python ${PYTHON_VERSION} Full Installer ==="

# Create resources directory
mkdir -p "$OUTPUT_DIR"

# Check if installer already exists (from cache)
if [ -f "$OUTPUT_DIR/python-${PYTHON_VERSION}-amd64.exe" ]; then
    echo "✅ Using cached Python installer"
else
    # Download Python installer (curl is cross-platform, wget is not on Windows)
    echo "Downloading Python installer..."
    curl -fSL --progress-bar -o "$OUTPUT_DIR/python-${PYTHON_VERSION}-amd64.exe" "$PYTHON_URL"

    # Verify download
    if [ ! -f "$OUTPUT_DIR/python-${PYTHON_VERSION}-amd64.exe" ]; then
        echo "ERROR: Download failed"
        exit 1
    fi
fi

# Get file size in a cross-platform way
if command -v stat &> /dev/null && stat --version &> /dev/null 2>&1; then
    # Linux (GNU stat)
    FILE_SIZE=$(stat -c%s "$OUTPUT_DIR/python-${PYTHON_VERSION}-amd64.exe")
elif command -v stat &> /dev/null; then
    # macOS (BSD stat)
    FILE_SIZE=$(stat -f%z "$OUTPUT_DIR/python-${PYTHON_VERSION}-amd64.exe")
else
    # Windows PowerShell fallback
    FILE_SIZE=$(powershell -Command "(Get-Item '$OUTPUT_DIR/python-${PYTHON_VERSION}-amd64.exe').Length")
fi
FILE_SIZE_MB=$((FILE_SIZE / 1024 / 1024))
echo "Downloaded: ${FILE_SIZE_MB} MB"

# Create requirements file for fi-monitor deps
cat > "$OUTPUT_DIR/fi-monitor-requirements.txt" <<EOF
fastapi==0.115.0
uvicorn[standard]==0.38.0
httpx==0.28.1
sentence-transformers==3.3.1
EOF

echo "✅ Python installer ready at: $OUTPUT_DIR"
