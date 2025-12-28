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

# SECURITY: Mock auth is BLOCKED in CI environments
# This prevents accidental production of auth-bypass builds
if [ -n "${CI:-}" ] || [ -n "${GITHUB_ACTIONS:-}" ] || [ -n "${GITLAB_CI:-}" ]; then
    if [ "${ENABLE_DESKTOP_MOCK_AUTH:-0}" = "1" ]; then
        echo ""
        echo "============================================================"
        echo "ERROR: ENABLE_DESKTOP_MOCK_AUTH=1 is FORBIDDEN in CI"
        echo "============================================================"
        echo "Mock authentication is only allowed for local development."
        echo "CI builds MUST use secure authentication."
        echo ""
        echo "If you need mock auth for testing, run locally:"
        echo "  ENABLE_DESKTOP_MOCK_AUTH=1 ./build.sh"
        echo "============================================================"
        exit 1
    fi
fi

# Security: Mock auth requires explicit opt-in via environment variable
# This prevents accidental builds with authentication bypass
if [ ! -f "$DESKTOP_ROOT/.env.desktop" ]; then
    if [ -f "$DESKTOP_ROOT/.env.desktop.example" ]; then
        if [ "${ENABLE_DESKTOP_MOCK_AUTH:-0}" = "1" ]; then
            echo ""
            echo "============================================================"
            echo "WARNING: Mock authentication ENABLED"
            echo "============================================================"
            echo "This build will bypass authentication."
            echo "ONLY use for offline desktop development."
            echo "NEVER distribute builds with mock auth enabled."
            echo "============================================================"
            echo ""
            sed 's/NEXT_PUBLIC_USE_MOCK_AUTH=false/NEXT_PUBLIC_USE_MOCK_AUTH=true/' \
                "$DESKTOP_ROOT/.env.desktop.example" > "$DESKTOP_ROOT/.env.desktop"
        else
            echo "Creating .env.desktop with SECURE defaults (mock auth disabled)"
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

# PyInstaller onefile mode produces a single executable at dist/aurity-backend
# (not a directory - this is required for Tauri sidecar)
EXECUTABLE="$SCRIPT_DIR/dist/aurity-backend"

# Verify PyInstaller produced the executable
if [ ! -f "$EXECUTABLE" ]; then
    echo "ERROR: Executable not found: $EXECUTABLE"
    echo ""
    echo "PyInstaller dist/ contents:"
    ls -la "$SCRIPT_DIR/dist/" 2>/dev/null || echo "  (dist/ directory not found)"
    echo ""
    echo "Make sure aurity-backend.spec uses onefile mode (no COLLECT)."
    exit 1
fi

# Copy the executable with platform suffix
echo "Copying executable to Tauri binaries directory..."
cp "$EXECUTABLE" "$BINARIES_DIR/aurity-backend$BINARY_SUFFIX"

# Make executable
chmod +x "$BINARIES_DIR/aurity-backend$BINARY_SUFFIX"

# Verify the copy was successful
if [ ! -x "$BINARIES_DIR/aurity-backend$BINARY_SUFFIX" ]; then
    echo "ERROR: Failed to create executable sidecar"
    echo "  Expected: $BINARIES_DIR/aurity-backend$BINARY_SUFFIX"
    exit 1
fi

echo "Sidecar created: $BINARIES_DIR/aurity-backend$BINARY_SUFFIX"
ls -lh "$BINARIES_DIR/aurity-backend$BINARY_SUFFIX"

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
