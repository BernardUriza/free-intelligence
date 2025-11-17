#!/usr/bin/env python3
"""Repair WebM chunks by grafting EBML headers.

Card: AUR-PROMPT-3.4
Created: 2025-11-09

Usage:
    python3 scripts/repair_webm_graft.py

Repairs all existing sessions in storage/audio by grafting chunk_0 header
onto chunks 1+ that lack EBML headers.

File: scripts/repair_webm_graft.py
"""

from __future__ import annotations

from pathlib import Path

from backend.workers.webm_graft import ensure_session_header, graft_header, is_ebml

root = Path("storage/audio")

print(f"🔧 Scanning sessions in {root.absolute()}")

total_sessions = 0
total_grafted = 0

for sess in sorted(root.glob("*")):
    if not sess.is_dir():
        continue

    total_sessions += 1

    try:
        hdr = ensure_session_header(sess)
        print(f"  ✓ Session {sess.name}: header cached ({len(hdr)} bytes)")
    except Exception as e:
        print(f"  ⚠️  Session {sess.name}: no header source ({e})")
        continue

    for raw in sorted(sess.glob("chunk_*.webm")):
        # Skip chunk 0 (header source)
        if raw.name.startswith("chunk_0"):
            continue

        # Skip already grafted
        if ".grafted" in raw.name:
            continue

        if not is_ebml(raw):
            try:
                out = graft_header(raw, hdr)
                print(f"    → Grafted: {out.name}")
                total_grafted += 1
            except Exception as e:
                print(f"    ✗ Failed to graft {raw.name}: {e}")

print("\n📊 Summary:")
print(f"  Sessions scanned: {total_sessions}")
print(f"  Chunks grafted:   {total_grafted}")
