#!/bin/bash
#
# Validate Release Artifacts
# Verifica que los artifacts del release sean válidos:
# - Existen todos los archivos esperados
# - Firmas Ed25519 son válidas
# - Tamaños son razonables (no archivos vacíos/corruptos)
#
# Usage: ./validate-release-artifacts.sh <version>
# Example: ./validate-release-artifacts.sh 1.0.0

set -euo pipefail

VERSION="${1:-}"
if [[ -z "$VERSION" ]]; then
  echo "❌ Error: Version required"
  echo "Usage: $0 <version>"
  echo "Example: $0 1.0.0"
  exit 1
fi

# SECURITY: Validate VERSION against strict semantic version pattern
# Prevents path traversal attacks (e.g., ../../home/user)
if [[ ! "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
  echo "❌ Error: Invalid version format"
  echo "Expected semantic version (e.g., 1.0.0)"
  echo "Got: ${VERSION}"
  exit 1
fi

REPO="BernardUriza/free-intelligence"
TAG="v${VERSION}"

# SECURITY: Use mktemp -d to create isolated temporary directory
# Never use rm -rf with user-controlled paths
# NOTE: Portable form (works on GNU/Linux, macOS, BSD)
DOWNLOAD_DIR=$(mktemp -d "${TMPDIR:-/tmp}/aurity-release-validation.XXXXXX")

# Cleanup function (safer than inline trap string)
cleanup() {
  # Use -- to prevent paths starting with - from being interpreted as flags
  rm -rf -- "$DOWNLOAD_DIR"
}

# Ensure cleanup on exit (even if script fails)
trap cleanup EXIT

echo "🔍 Validating release artifacts for ${TAG}"
echo "📁 Download directory: ${DOWNLOAD_DIR}"
echo ""

cd "$DOWNLOAD_DIR"

# Expected artifacts
declare -A ARTIFACTS=(
  ["Aurity_${VERSION}_aarch64.dmg"]="macOS DMG"
  ["Aurity_${VERSION}_aarch64.dmg.sig"]="macOS Signature"
  ["Aurity_${VERSION}_amd64.AppImage"]="Linux AppImage"
  ["Aurity_${VERSION}_amd64.AppImage.sig"]="Linux Signature"
  ["Aurity_${VERSION}_x64-setup.nsis.zip"]="Windows NSIS"
  ["Aurity_${VERSION}_x64-setup.nsis.zip.sig"]="Windows Signature"
  ["aurity-desktop-updater.json"]="Updater Manifest"
)

# Expected minimum sizes (bytes)
declare -A MIN_SIZES=(
  ["Aurity_${VERSION}_aarch64.dmg"]=50000000        # 50MB
  ["Aurity_${VERSION}_amd64.AppImage"]=50000000     # 50MB
  ["Aurity_${VERSION}_x64-setup.nsis.zip"]=30000000 # 30MB
  ["aurity-desktop-updater.json"]=100               # 100 bytes
)

echo "📥 Downloading artifacts from ${TAG}..."
echo ""

FAILURES=0

for FILE in "${!ARTIFACTS[@]}"; do
  DESC="${ARTIFACTS[$FILE]}"
  echo -n "  Downloading ${DESC}... "

  if gh release download "$TAG" -R "$REPO" -p "$FILE" 2>/dev/null; then
    echo "✅"
  else
    echo "❌ FAILED"
    ((FAILURES++))
    continue
  fi

  # Check file size
  if [[ -v MIN_SIZES[$FILE] ]]; then
    SIZE=$(stat -f%z "$FILE" 2>/dev/null || stat -c%s "$FILE" 2>/dev/null)
    MIN_SIZE="${MIN_SIZES[$FILE]}"

    if [[ $SIZE -lt $MIN_SIZE ]]; then
      echo "    ❌ Size too small: ${SIZE} bytes (expected >${MIN_SIZE})"
      ((FAILURES++))
    else
      SIZE_MB=$((SIZE / 1024 / 1024))
      echo "    ✅ Size OK: ${SIZE_MB}MB"
    fi
  fi
done

echo ""
echo "🔐 Verifying Ed25519 signatures..."
echo ""

# Verify signatures
for BINARY in "Aurity_${VERSION}_aarch64.dmg" "Aurity_${VERSION}_amd64.AppImage" "Aurity_${VERSION}_x64-setup.nsis.zip"; do
  SIG_FILE="${BINARY}.sig"

  if [[ ! -f "$BINARY" ]] || [[ ! -f "$SIG_FILE" ]]; then
    echo "  ⏭️  Skipping ${BINARY} (missing file)"
    continue
  fi

  echo -n "  Verifying ${BINARY}... "

  # Extract signature from .sig file (base64 encoded)
  SIGNATURE=$(cat "$SIG_FILE")

  # Verify using Tauri signer (requires tauri-cli installed)
  if command -v tauri &> /dev/null; then
    if tauri signer verify "$BINARY" "$SIGNATURE" &> /dev/null; then
      echo "✅ Valid signature"
    else
      echo "❌ INVALID SIGNATURE"
      ((FAILURES++))
    fi
  else
    echo "⚠️  Skipped (tauri-cli not installed)"
  fi
done

echo ""
echo "📄 Validating updater manifest..."
echo ""

if [[ -f "aurity-desktop-updater.json" ]]; then
  # Check JSON syntax
  if jq empty "aurity-desktop-updater.json" 2>/dev/null; then
    echo "  ✅ Valid JSON syntax"

    # Check required fields
    MANIFEST_VERSION=$(jq -r '.version' aurity-desktop-updater.json)
    PLATFORMS=$(jq -r '.platforms | keys | .[]' aurity-desktop-updater.json)

    echo "  📌 Version: ${MANIFEST_VERSION}"

    if [[ "$MANIFEST_VERSION" != "$VERSION" ]]; then
      echo "  ❌ Version mismatch: expected ${VERSION}, got ${MANIFEST_VERSION}"
      ((FAILURES++))
    else
      echo "  ✅ Version matches"
    fi

    echo "  📦 Platforms:"
    for PLATFORM in $PLATFORMS; do
      SIGNATURE=$(jq -r ".platforms[\"$PLATFORM\"].signature" aurity-desktop-updater.json)
      URL=$(jq -r ".platforms[\"$PLATFORM\"].url" aurity-desktop-updater.json)

      if [[ -z "$SIGNATURE" ]] || [[ "$SIGNATURE" == "null" ]]; then
        echo "    ❌ ${PLATFORM}: Missing signature"
        ((FAILURES++))
      else
        SIG_LEN=${#SIGNATURE}
        echo "    ✅ ${PLATFORM}: Signature present (${SIG_LEN} chars)"
      fi

      if [[ -z "$URL" ]] || [[ "$URL" == "null" ]]; then
        echo "    ❌ ${PLATFORM}: Missing URL"
        ((FAILURES++))
      else
        echo "       URL: ${URL}"
      fi
    done
  else
    echo "  ❌ Invalid JSON"
    ((FAILURES++))
  fi
else
  echo "  ❌ Manifest not found"
  ((FAILURES++))
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [[ $FAILURES -eq 0 ]]; then
  echo "✅ All validations passed!"
  echo "📂 Artifacts downloaded to: ${DOWNLOAD_DIR}"
  exit 0
else
  echo "❌ Validation failed with ${FAILURES} error(s)"
  echo "📂 Check artifacts at: ${DOWNLOAD_DIR}"
  exit 1
fi
