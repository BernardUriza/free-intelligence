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
    # Download Python installer
    echo "Downloading Python installer..."
    wget -q --show-progress -O "$OUTPUT_DIR/python-${PYTHON_VERSION}-amd64.exe" "$PYTHON_URL"

    # Verify download
    if [ ! -f "$OUTPUT_DIR/python-${PYTHON_VERSION}-amd64.exe" ]; then
        echo "ERROR: Download failed"
        exit 1
    fi
fi

FILE_SIZE=$(stat -f%z "$OUTPUT_DIR/python-${PYTHON_VERSION}-amd64.exe" 2>/dev/null || stat -c%s "$OUTPUT_DIR/python-${PYTHON_VERSION}-amd64.exe")
echo "Downloaded: $(numfmt --to=iec-i --suffix=B $FILE_SIZE)"

# Create requirements file for fi-monitor deps
cat > "$OUTPUT_DIR/fi-monitor-requirements.txt" <<EOF
fastapi==0.115.0
uvicorn[standard]==0.38.0
httpx==0.28.1
sentence-transformers==3.3.1
EOF

echo "✅ Python installer ready at: $OUTPUT_DIR"
