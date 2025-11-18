#!/bin/bash
# Free Intelligence - Generate Self-Signed TLS Certificate
# HIPAA Card: G-002 - Cifrado en tránsito
# Author: Bernard Uriza Orozco
# Created: 2025-11-17

set -e

echo "🔐 Generating self-signed TLS certificate for Free Intelligence..."

# Create certs directory
CERT_DIR="/Users/bernardurizaorozco/Documents/free-intelligence/config/nginx/certs"
mkdir -p "$CERT_DIR"

# Certificate details
COUNTRY="MX"
STATE="Mexico"
CITY="Mexico City"
ORG="Free Intelligence"
OU="AURITY"
CN="localhost"
DAYS=365

echo ""
echo "📋 Certificate details:"
echo "   Country: $COUNTRY"
echo "   State: $STATE"
echo "   City: $CITY"
echo "   Organization: $ORG"
echo "   Common Name: $CN"
echo "   Validity: $DAYS days"
echo ""

# Generate private key (RSA 4096 bits - HIPAA best practice)
echo "🔑 Generating 4096-bit RSA private key..."
openssl genrsa -out "$CERT_DIR/server.key" 4096

# Set secure permissions on private key
chmod 600 "$CERT_DIR/server.key"
echo "   ✅ Private key generated: $CERT_DIR/server.key"

# Generate certificate signing request (CSR)
echo ""
echo "📝 Generating Certificate Signing Request (CSR)..."
openssl req -new -key "$CERT_DIR/server.key" \
    -out "$CERT_DIR/server.csr" \
    -subj "/C=$COUNTRY/ST=$STATE/L=$CITY/O=$ORG/OU=$OU/CN=$CN"
echo "   ✅ CSR generated: $CERT_DIR/server.csr"

# Generate self-signed certificate (valid for 1 year)
echo ""
echo "🎫 Generating self-signed certificate..."
openssl x509 -req -days $DAYS \
    -in "$CERT_DIR/server.csr" \
    -signkey "$CERT_DIR/server.key" \
    -out "$CERT_DIR/server.crt" \
    -sha256 \
    -extfile <(printf "subjectAltName=DNS:localhost,IP:127.0.0.1")
echo "   ✅ Certificate generated: $CERT_DIR/server.crt"

# Clean up CSR (no longer needed)
rm "$CERT_DIR/server.csr"

# Display certificate info
echo ""
echo "📄 Certificate information:"
openssl x509 -in "$CERT_DIR/server.crt" -text -noout | grep -A 2 "Validity"
openssl x509 -in "$CERT_DIR/server.crt" -text -noout | grep "Subject:"
openssl x509 -in "$CERT_DIR/server.crt" -text -noout | grep "Subject Alternative Name" -A 1

# Calculate SHA-256 fingerprint (for HIPAA evidence)
echo ""
echo "🔍 Certificate SHA-256 fingerprint:"
FINGERPRINT=$(openssl x509 -in "$CERT_DIR/server.crt" -noout -fingerprint -sha256)
echo "   $FINGERPRINT"

# Save fingerprint to file (for evidence/auditing)
echo "$FINGERPRINT" > "$CERT_DIR/server.crt.sha256"

echo ""
echo "✅ TLS certificate generation complete!"
echo ""
echo "📁 Files created:"
echo "   • Private key: $CERT_DIR/server.key (chmod 600)"
echo "   • Certificate: $CERT_DIR/server.crt"
echo "   • SHA-256:     $CERT_DIR/server.crt.sha256"
echo ""
echo "⚠️  SECURITY NOTE:"
echo "   This is a SELF-SIGNED certificate for DEVELOPMENT only."
echo "   For PRODUCTION, use Let's Encrypt or a trusted CA."
echo ""
echo "🚀 Next steps:"
echo "   1. Start nginx: brew services start nginx"
echo "   2. Test HTTPS: curl -k https://localhost/health"
echo "   3. Verify TLS 1.3: testssl.sh https://localhost"
echo ""
