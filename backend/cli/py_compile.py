#!/usr/bin/env python3
"""
QA: Compile all Python files to detect syntax errors without execution.
Reports JSON output to /tmp/fi-artifacts/pycompile_report.json
"""
import json
import os
import py_compile
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(".")
SKIP = {".venv", "venv", "node_modules", "__pycache__", ".git", ".mypy_cache", ".pytest_cache"}
errors = []
files = []

print("Scanning Python files...")
for p in ROOT.rglob("*.py"):
    parts = set(p.parts)
    if parts & SKIP:
        continue
    try:
        py_compile.compile(str(p), doraise=True)
        files.append(str(p))
    except py_compile.PyCompileError as e:
        errors.append({"file": str(p), "error": str(e)})
    except Exception as e:
        errors.append({"file": str(p), "error": f"{type(e).__name__}: {str(e)}"})

report = {
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "total": len(files) + len(errors),
    "ok": len(files),
    "fail": len(errors),
    "success_rate": round(100 * len(files) / (len(files) + len(errors)), 2)
    if (len(files) + len(errors)) > 0
    else 0,
    "errors": errors,
    "files_ok_sample": sorted(files)[:10],  # Sample
}

os.makedirs("/tmp/fi-artifacts", exist_ok=True)
with open("/tmp/fi-artifacts/pycompile_report.json", "w") as f:
    json.dump(report, f, indent=2)

print(json.dumps(report, indent=2))
sys.exit(1 if errors else 0)
