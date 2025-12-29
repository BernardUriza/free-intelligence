#!/bin/bash
# =============================================================================
# Aurity Desktop: Local TLS Certificate Setup with mkcert
# =============================================================================
#
# This script sets up local TLS certificates for development using mkcert.
# mkcert creates a local Certificate Authority (CA) that is trusted by your
# system, allowing HTTPS without browser warnings.
#
# Usage:
#   ./scripts/setup-dev-tls.sh
#
# After running:
#   - Certificates are saved to ~/.aurity/certs/
#   - Local CA is installed and trusted by the system
#   - You can use HTTPS on localhost without warnings
#
# =============================================================================

set -e

echo "=== Aurity Desktop: TLS Certificate Setup ==="
echo ""

# Check if running on macOS or Linux
if [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
else
    echo "Error: Unsupported operating system: $OSTYPE"
    echo "This script supports macOS and Linux only."
    exit 1
fi

# Check if mkcert is installed
if ! command -v mkcert &> /dev/null; then
    echo "mkcert not found. Installing..."

    if [[ "$OS" == "macos" ]]; then
        if command -v brew &> /dev/null; then
            brew install mkcert
        else
            echo "Error: Homebrew is required to install mkcert on macOS."
            echo "Install Homebrew from: https://brew.sh"
            exit 1
        fi
    else
        # Linux
        if command -v apt &> /dev/null; then
            sudo apt update && sudo apt install -y mkcert
        elif command -v yum &> /dev/null; then
            sudo yum install -y mkcert
        else
            echo "Error: Please install mkcert manually."
            echo "See: https://github.com/FiloSottile/mkcert#installation"
            exit 1
        fi
    fi

    echo "mkcert installed successfully."
fi

# Install local CA (this makes browsers trust our certificates)
echo ""
echo "Installing local Certificate Authority..."
mkcert -install
echo "Local CA installed and trusted."

# Create certificates directory
CERT_DIR="$HOME/.aurity/certs"
mkdir -p "$CERT_DIR"

# Generate certificates
echo ""
echo "Generating certificates..."
cd "$CERT_DIR"
mkcert localhost 127.0.0.1 ::1

# Rename to more predictable names
mv localhost+2.pem localhost.pem 2>/dev/null || true
mv localhost+2-key.pem localhost-key.pem 2>/dev/null || true

# Set secure permissions
chmod 600 "$CERT_DIR"/*.pem

echo ""
echo "=== TLS Certificates Generated ==="
echo ""
echo "Location: $CERT_DIR"
echo "Files:"
echo "  - localhost.pem      (certificate)"
echo "  - localhost-key.pem  (private key)"
echo ""
echo "To use with the local backend, set environment variables:"
echo ""
echo "  export SSL_CERT_FILE=$CERT_DIR/localhost.pem"
echo "  export SSL_KEY_FILE=$CERT_DIR/localhost-key.pem"
echo ""
echo "Or add to your .env.local:"
echo ""
echo "  SSL_CERT_FILE=$CERT_DIR/localhost.pem"
echo "  SSL_KEY_FILE=$CERT_DIR/localhost-key.pem"
echo ""
echo "=== Setup Complete ==="
