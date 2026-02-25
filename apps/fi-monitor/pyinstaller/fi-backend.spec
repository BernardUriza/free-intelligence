# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for FI Backend sidecar (Gateway + RAG Service).

Creates a standalone executable bundling both services as CLI subcommands.

Build command:
    pyinstaller fi-backend.spec

Output:
    dist/fi-backend-<target-triple> (single executable)
"""

import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules

# Project paths
# SPECPATH is provided by PyInstaller and points to the spec file directory
FI_MONITOR_ROOT = Path(SPECPATH).parent.absolute()
GATEWAY_DIR = FI_MONITOR_ROOT / "gateway"
RAG_SERVICE_DIR = FI_MONITOR_ROOT / "rag_service"

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
print(f"FI Monitor root: {FI_MONITOR_ROOT}")

# Verify paths exist
def check_path(path, description):
    if not path.exists():
        print(f"\n{'='*60}")
        print(f"ERROR: {description}")
        print(f"{'='*60}")
        print(f"Expected path: {path}")
        print(f"\nTo fix this:")
        print(f"  1. cd apps/fi-monitor/pyinstaller")
        print(f"  2. pip install -r requirements.txt")
        print(f"  3. pip install -r ../gateway/requirements.txt")
        print(f"  4. pip install -r ../rag_service/requirements.txt")
        print(f"  5. pyinstaller fi-backend.spec")
        print(f"{'='*60}\n")
        sys.exit(1)

check_path(GATEWAY_DIR, "Gateway directory not found")
check_path(RAG_SERVICE_DIR, "RAG Service directory not found")

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
    # HTTP client (gateway)
    "httpx",
    "httpcore",
    # ML / RAG Service
    "torch",
    "sentence_transformers",
    "numpy",
    "scipy",
    "sklearn",
    "PyPDF2",
    # System monitoring
    "psutil",
    # Async support
    "anyio",
    "anyio._backends",
    "anyio._backends._asyncio",
    # Local modules (datas copies full directories; runtime_hook.py fixes bare imports)
    "gateway",
    "gateway.main",
    "rag_service",
    "rag_service.main",
    "rag_service.annotations",
    "rag_service.metrics",
]

# Collect all submodules from key packages
for pkg in ["fastapi", "starlette", "torch", "sentence_transformers", "sklearn", "scipy"]:
    try:
        hidden_imports.extend(collect_submodules(pkg))
    except Exception as e:
        print(f"Warning: Could not collect submodules for {pkg}: {e}")

# Data files to include
datas = [
    # Include gateway and rag_service as data (they're imported at runtime)
    (str(GATEWAY_DIR), "gateway"),
    (str(RAG_SERVICE_DIR), "rag_service"),
]

# Filter out non-existent paths
datas = [(src, dst) for src, dst in datas if Path(src).exists()]

# Exclude packages not needed (reduce size)
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
    # Not needed
    "tkinter",
    "matplotlib",
    "pandas",
    "PIL",
]

a = Analysis(
    [str(FI_MONITOR_ROOT / "pyinstaller" / "fi-backend-entry.py")],
    pathex=[str(FI_MONITOR_ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[str(Path(SPECPATH) / "runtime_hook.py")],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# IMPORTANT: Tauri sidecar requires a SINGLE EXECUTABLE file
# Using onefile mode (include all binaries in EXE, no COLLECT)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,      # Include binaries in EXE (onefile mode)
    a.zipfiles,      # Include zipfiles in EXE (onefile mode)
    a.datas,         # Include datas in EXE (onefile mode)
    [],
    name=f"fi-backend-{TARGET_TRIPLE}",
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=False,  # Disabled: UPX not guaranteed on all CI runners
    console=True,  # Keep console for log output
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# NOTE: No COLLECT step - we produce a single executable file
# Output: dist/fi-backend-<target-triple> (single file)
# Copy to apps/fi-monitor/src-tauri/binaries/ before building Tauri
