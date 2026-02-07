# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Aurity Backend sidecar.

This creates a standalone executable that can be bundled with Tauri.

Build command:
    pyinstaller aurity-backend.spec

Output:
    dist/aurity-backend-<target-triple> (single executable)
"""

import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules, collect_all

# Project paths
# SPECPATH is provided by PyInstaller and points to the spec file directory
PROJECT_ROOT = Path(SPECPATH).parent.parent.parent.absolute()
BACKEND_ROOT = PROJECT_ROOT / "backend"
BACKEND_APP = BACKEND_ROOT / "app"

# Platform detection for cross-platform builds
import platform
SYSTEM = sys.platform
MACHINE = platform.machine().lower()

# Determine target triple for output naming
if SYSTEM == "win32":
    TARGET_TRIPLE = "x86_64-pc-windows-msvc"
    EXE_EXTENSION = ".exe"
elif SYSTEM == "darwin":
    TARGET_TRIPLE = "aarch64-apple-darwin" if MACHINE == "arm64" else "x86_64-apple-darwin"
    EXE_EXTENSION = ""
else:  # Linux
    TARGET_TRIPLE = "x86_64-unknown-linux-gnu"
    EXE_EXTENSION = ""

print(f"Building for platform: {SYSTEM} ({MACHINE})")
print(f"Target triple: {TARGET_TRIPLE}")
print(f"Backend root: {BACKEND_ROOT}")

# Verify paths exist
def check_path(path, description):
    """Check if a path exists and provide a helpful error message if not."""
    if not path.exists():
        print(f"\n{'='*60}")
        print(f"ERROR: {description}")
        print(f"{'='*60}")
        print(f"Expected path: {path}")
        print(f"\nTo fix this:")
        print(f"  1. Ensure you're running from the correct directory")
        print(f"  2. Run: cd apps/aurity-desktop/pyinstaller")
        print(f"  3. Run: pyinstaller aurity-backend.spec")
        print(f"{'='*60}\n")
        sys.exit(1)

check_path(BACKEND_ROOT, "Backend root directory not found")
check_path(BACKEND_APP, "Backend app directory not found")

block_cipher = None

# Hidden imports that PyInstaller might miss
hidden_imports = [
    # FastAPI and web framework
    "fastapi",
    "uvicorn",
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "starlette",
    "starlette.routing",
    "starlette.middleware",
    "starlette.middleware.cors",
    "pydantic",
    "pydantic_settings",
    # HTTP client
    "httpx",
    "httpcore",
    # Database
    "h5py",
    "sqlalchemy",
    "sqlalchemy.ext.asyncio",
    "alembic",
    # Ollama client
    "ollama",
    # Async support
    "anyio",
    "anyio._backends",
    "anyio._backends._asyncio",
    # Backend modules (new architecture)
    "backend",
    "backend.app",
    "backend.api",
    "backend.clients",
    "backend.domain",
    "backend.infrastructure",
    "backend.middleware",
    "backend.models",
    "backend.observability",
    "backend.policy",
    "backend.providers",
    "backend.repositories",
    "backend.schemas",
    "backend.services",
    "backend.utils",
    # Payment (stub for import compatibility)
    "stripe",
    # System monitoring
    "psutil",
    # JWT/Auth
    "jose",
    "passlib",
    "bcrypt",
    # Metrics
    "prometheus_client",
    # Structlog
    "structlog",
]

# Collect all submodules from key packages
for pkg in ["backend", "stripe", "sqlalchemy", "fastapi", "starlette"]:
    try:
        hidden_imports.extend(collect_submodules(pkg))
    except Exception as e:
        print(f"Warning: Could not collect submodules for {pkg}: {e}")

# Collect stripe data (binaries, datas, hiddenimports)
try:
    stripe_datas, stripe_binaries, stripe_hiddenimports = collect_all("stripe")
    hidden_imports.extend(stripe_hiddenimports)
except Exception:
    stripe_datas = []
    stripe_binaries = []

# Data files to include
# Include the entire backend directory structure
datas = [
    # Include all backend Python modules
    (str(BACKEND_ROOT / "api"), "backend/api"),
    (str(BACKEND_ROOT / "app"), "backend/app"),
    (str(BACKEND_ROOT / "clients"), "backend/clients"),
    (str(BACKEND_ROOT / "domain"), "backend/domain"),
    (str(BACKEND_ROOT / "infrastructure"), "backend/infrastructure"),
    (str(BACKEND_ROOT / "middleware"), "backend/middleware"),
    (str(BACKEND_ROOT / "models"), "backend/models"),
    (str(BACKEND_ROOT / "observability"), "backend/observability"),
    (str(BACKEND_ROOT / "policy"), "backend/policy"),
    (str(BACKEND_ROOT / "providers"), "backend/providers"),
    (str(BACKEND_ROOT / "repositories"), "backend/repositories"),
    (str(BACKEND_ROOT / "schemas"), "backend/schemas"),
    (str(BACKEND_ROOT / "services"), "backend/services"),
    (str(BACKEND_ROOT / "utils"), "backend/utils"),
    (str(BACKEND_ROOT / "mappers"), "backend/mappers"),
    (str(BACKEND_ROOT / "validators"), "backend/validators"),
    (str(BACKEND_ROOT / "workflows_core"), "backend/workflows_core"),
    (str(BACKEND_ROOT / "security_core"), "backend/security_core"),
    # NOTE: config/ directory is NOT bundled (may contain secrets)
    # Desktop app creates config at ~/.aurity/config/ on first run
]

# Filter out non-existent paths
datas = [(src, dst) for src, dst in datas if Path(src).exists()]

# Warn about excluded directories
excluded_dirs = ['config', 'tests', 'scripts', 'debug', 'examples', 'docs']
for dirname in excluded_dirs:
    dirpath = BACKEND_ROOT / dirname
    if dirpath.exists():
        print(f"NOTE: {dirname}/ directory NOT bundled (security/size)")

# Exclude packages not needed for desktop (reduce size)
excludes = [
    # Testing
    "pytest",
    "pytest_asyncio",
    "pytest_cov",
    "_pytest",
    # Development tools
    "ipython",
    "jupyter",
    "notebook",
    "IPython",
    # Unused cloud services (for offline mode)
    "twilio",
    "sendgrid",
]

a = Analysis(
    [str(BACKEND_APP / "main.py")],
    pathex=[str(BACKEND_ROOT), str(PROJECT_ROOT)],
    binaries=stripe_binaries,
    datas=datas + stripe_datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# IMPORTANT: Tauri sidecar requires a SINGLE EXECUTABLE file
# Using onefile mode (include all binaries in EXE, no COLLECT)
# Output name includes target triple for multi-platform builds
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,      # Include binaries in EXE (onefile mode)
    a.zipfiles,      # Include zipfiles in EXE (onefile mode)
    a.datas,         # Include datas in EXE (onefile mode)
    [],
    name=f"aurity-backend-{TARGET_TRIPLE}",
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=False,  # Disabled: UPX not guaranteed on all CI runners
    console=True,  # Keep console for debugging; set False for release
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# NOTE: No COLLECT step - we produce a single executable file
# Output: dist/aurity-backend-<target-triple> (single file)
# This is required for Tauri sidecar to work correctly
