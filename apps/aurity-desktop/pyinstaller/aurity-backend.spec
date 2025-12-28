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

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.absolute()
BACKEND_ROOT = PROJECT_ROOT / "backend"
BACKEND_SRC = BACKEND_ROOT / "src"
BACKEND_APP = BACKEND_ROOT / "app"

# Verify paths exist
assert BACKEND_ROOT.exists(), f"Backend root not found: {BACKEND_ROOT}"
assert BACKEND_SRC.exists(), f"Backend src not found: {BACKEND_SRC}"

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
]

# Data files to include
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
    # Config files
    (str(BACKEND_ROOT / "config"), "config"),
    # Policy files
    (str(BACKEND_ROOT / "policy"), "policy"),
]

# Filter out non-existent paths
datas = [(src, dst) for src, dst in datas if Path(src).exists()]

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
    "stripe",
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
    binaries=[],
    datas=datas,
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

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="aurity-backend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=True,
    console=True,  # Keep console for debugging; set False for release
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=True,
    upx=True,
    upx_exclude=[],
    name="aurity-backend",
)
