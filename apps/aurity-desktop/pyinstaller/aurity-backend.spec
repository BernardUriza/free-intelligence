# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Aurity Backend sidecar.

This creates a standalone executable that can be bundled with Tauri.

Build command:
    pyinstaller aurity-backend.spec

Output:
    dist/aurity-backend (macOS/Linux)
    dist/aurity-backend.exe (Windows)
"""

import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules, collect_all

# Project paths
# Note: SPECPATH is provided by PyInstaller and points to the spec file directory
# Using SPECPATH instead of __file__ for Python 3.14 compatibility
PROJECT_ROOT = Path(SPECPATH).parent.parent.parent.absolute()
BACKEND_ROOT = PROJECT_ROOT / "backend"
BACKEND_SRC = BACKEND_ROOT / "src"
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

# Verify paths exist with helpful error messages
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
        print(f"  3. Run: ./build.sh")
        print(f"\nProject structure expected:")
        print(f"  free-intelligence/")
        print(f"  ├── backend/")
        print(f"  │   ├── src/")
        print(f"  │   └── app/")
        print(f"  └── apps/aurity-desktop/pyinstaller/")
        print(f"{'='*60}\n")
        sys.exit(1)

check_path(BACKEND_ROOT, "Backend root directory not found")
check_path(BACKEND_SRC, "Backend src directory not found")

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
    # Ollama client
    "ollama",
    # Our modules
    "fi_common",
    "fi_common.config",
    "fi_common.config.deployment",
    "fi_common.logging",
    "fi_storage",
    "fi_auth",
    "fi_workflow",
    "fi_assistant",
    "fi_llm",
    # Async support
    "anyio",
    "anyio._backends",
    "anyio._backends._asyncio",
    # Payment (stub for import compatibility - not used in desktop mode)
    "stripe",
    # System monitoring
    "psutil",
] + collect_submodules("stripe")

# Collect all stripe data (binaries, datas, hiddenimports)
stripe_datas, stripe_binaries, stripe_hiddenimports = collect_all("stripe")
hidden_imports = hidden_imports + stripe_hiddenimports

# Data files to include
# SECURITY: Only include code modules, NOT config files that may contain secrets
# Config is loaded at runtime from user's data directory
datas = [
    # Include all fi_* modules from backend/src
    (str(BACKEND_SRC / "fi_common"), "fi_common"),
    (str(BACKEND_SRC / "fi_storage"), "fi_storage"),
    (str(BACKEND_SRC / "fi_auth"), "fi_auth"),
    (str(BACKEND_SRC / "fi_workflow"), "fi_workflow"),
    (str(BACKEND_SRC / "fi_assistant"), "fi_assistant"),
    (str(BACKEND_SRC / "fi_llm"), "fi_llm"),
    (str(BACKEND_SRC / "fi_session"), "fi_session"),
    (str(BACKEND_SRC / "fi_transcription"), "fi_transcription"),
    (str(BACKEND_SRC / "fi_tts"), "fi_tts"),
    (str(BACKEND_SRC / "fi_model_catalog"), "fi_model_catalog"),
    (str(BACKEND_SRC / "fi_payment"), "fi_payment"),
    (str(BACKEND_SRC / "fi_checkin"), "fi_checkin"),
    (str(BACKEND_SRC / "fi_audit"), "fi_audit"),
    # NOTE: config/ and policy/ directories are NOT bundled
    # - Config may contain secrets or environment-specific settings
    # - Policy is bundled inline in fi_workflow module
    # - Desktop app creates config at ~/.aurity/config/ on first run
]

# Filter out non-existent paths
datas = [(src, dst) for src, dst in datas if Path(src).exists()]

# Warn about excluded directories
excluded_dirs = ['config', 'policy']
for dirname in excluded_dirs:
    dirpath = BACKEND_ROOT / dirname
    if dirpath.exists():
        print(f"NOTE: {dirname}/ directory NOT bundled (security: may contain secrets)")

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
    # Note: stripe is REQUIRED for import compatibility even if not used
    "twilio",
    "sendgrid",
    # Large ML packages (if not using local embeddings)
    # Uncomment these if you want a smaller build without sentence-transformers
    # "torch",
    # "transformers",
    # "sentence_transformers",
]

a = Analysis(
    [str(BACKEND_APP / "main.py")],
    pathex=[str(BACKEND_SRC), str(BACKEND_ROOT)],
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
    upx=False,  # Disabled: UPX not guaranteed to be available on all CI runners
    console=True,  # Keep console for debugging; set False for release
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# NOTE: No COLLECT step - we produce a single executable file
# Output: dist/aurity-backend (single file, not directory)
# This is required for Tauri sidecar to work correctly
