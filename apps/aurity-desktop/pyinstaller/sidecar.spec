# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Aurity Backend Sidecar

This creates a standalone executable that runs the FastAPI backend.
The executable will be placed in binaries/ with the correct Tauri naming.

Build with:
    cd apps/aurity-desktop/pyinstaller
    pyinstaller sidecar.spec
"""

import platform
import sys

# Determine the target triple for Tauri
system = platform.system().lower()
machine = platform.machine().lower()

if system == "windows":
    if machine in ("amd64", "x86_64"):
        target_triple = "x86_64-pc-windows-msvc"
    else:
        target_triple = "i686-pc-windows-msvc"
    exe_suffix = ".exe"
elif system == "darwin":
    if machine == "arm64":
        target_triple = "aarch64-apple-darwin"
    else:
        target_triple = "x86_64-apple-darwin"
    exe_suffix = ""
else:  # Linux
    if machine in ("aarch64", "arm64"):
        target_triple = "aarch64-unknown-linux-gnu"
    else:
        target_triple = "x86_64-unknown-linux-gnu"
    exe_suffix = ""

output_name = f"aurity-backend-{target_triple}"

a = Analysis(
    ['sidecar_entry.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'uvicorn',
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        'fastapi',
        'starlette',
        'pydantic',
        'httpx',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=output_name,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Keep console for logging
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# Copy to binaries folder after build
import shutil
import os

output_path = os.path.join('dist', output_name + exe_suffix)
binaries_path = os.path.join('..', 'src-tauri', 'binaries', output_name + exe_suffix)

print(f"[PostBuild] Output: {output_path}")
print(f"[PostBuild] Target: {binaries_path}")
