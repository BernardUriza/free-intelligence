"""WebM Header Grafting for RecordRTC Chunk Repair.

⚠️ DEPRECATED (2025-11-10) - NO LONGER NEEDED ⚠️

Card: AUR-PROMPT-3.4 (OLD) → AUR-PROMPT-4.2 (NEW FIX)
Created: 2025-11-09
Deprecated: 2025-11-10

Problem (OLD):
- RecordRTC chunks > 0 arrive as raw Opus (no EBML header)
- FFmpeg fails: "EBML header parsing failed"

Solution (OLD - DEPRECATED):
- Extract header from chunk_0.webm (has EBML)
- Graft header onto raw chunks before ffmpeg decode
- ISSUE: Segment size mismatch caused corruption

Solution (NEW - PRODUCTION):
- Frontend uses RecordRTC stop/start loop pattern
- Each chunk is a COMPLETE recording with full headers
- 100% chunks have headers (not just chunk 0)
- FFmpeg decodes all chunks without modification
- See: apps/aurity/lib/recording/makeRecorder.ts

This module remains for legacy MediaRecorder fallback but is
disabled by default: AURITY_ENABLE_WEBM_GRAFT=false

File: backend/workers/webm_graft.py
"""

from __future__ import annotations

import shutil
import time
from pathlib import Path
from typing import Optional

EBML_MAGIC = b"\x1A\x45\xDF\xA3"
EBML_CLUSTER_ID = b"\x1F\x43\xB6\x75"  # "Cluster"


def is_ebml(path: Path) -> bool:
    """Check if file starts with EBML magic bytes."""
    try:
        with open(path, "rb") as f:
            return f.read(4) == EBML_MAGIC
    except Exception:
        return False


def _extract_header_bytes(webm_bytes: bytes) -> bytes:
    """
    Extract WebM header (everything before first Cluster element).

    IMPORTANT: RecordRTC chunks > 0 are headerless BUT already contain
    their own Cluster elements. We must NOT include any Cluster data
    from chunk_0, only the EBML + Segment + Tracks metadata.
    """
    idx = webm_bytes.find(EBML_CLUSTER_ID)
    if idx == -1:
        # No Cluster found - unlikely but cap at safe size
        return webm_bytes[: min(len(webm_bytes), 8192)]

    # Return everything BEFORE the first Cluster
    # This ensures we only get: EBML header + Segment info + Tracks + Codecs
    return webm_bytes[:idx]


def _candidate_chunk0_paths(sess_dir: Path) -> list[Path]:
    """Return candidate paths for chunk 0 (supports multiple naming)."""
    # Soporta 0.webm, chunk_0.webm y variantes grafted
    names = ["0.webm", "chunk_0.webm", "0.grafted.webm", "chunk_0.grafted.webm"]
    return [sess_dir / n for n in names]


def wait_for_chunk0(sess_dir: Path, timeout: float = 3.0) -> Optional[Path]:
    """
    Wait for chunk 0 to be available (race condition killer).

    Chunks > 0 may arrive before chunk 0 is fully written.
    This helper polls for chunk 0 existence with timeout.

    Args:
        sess_dir: Session directory
        timeout: Max wait time in seconds

    Returns:
        Path to chunk 0 if found, None if timeout
    """
    deadline = time.time() + timeout

    # Quick check first (no wait)
    for p in _candidate_chunk0_paths(sess_dir):
        if p.exists() and p.stat().st_size > 0:
            return p

    # Poll with backoff
    while time.time() < deadline:
        for p in _candidate_chunk0_paths(sess_dir):
            if p.exists() and p.stat().st_size > 0:
                return p
        time.sleep(0.05)  # 50ms poll interval

    return None


def ensure_session_header(sess_dir: Path) -> bytes:
    """Get or extract WebM header for session (cached in _header.bin)."""
    cache = sess_dir / "_header.bin"
    if cache.exists():
        return cache.read_bytes()

    # Busca un chunk 0 válido
    for p in _candidate_chunk0_paths(sess_dir):
        if p.exists():
            data = p.read_bytes()
            hb = _extract_header_bytes(data)
            cache.write_bytes(hb)
            return hb

    # Fallback: primer .webm con EBML
    for p in sorted(sess_dir.glob("*.webm")):
        try:
            b4 = p.read_bytes()[:4]
            if b4 == EBML_MAGIC:
                hb = _extract_header_bytes(p.read_bytes())
                cache.write_bytes(hb)
                return hb
        except Exception:
            continue

    raise FileNotFoundError("No EBML header source found (chunk 0 missing?)")


def graft_header(raw: Path, header: bytes) -> Path:
    """Graft WebM header onto raw Opus chunk, return grafted path."""
    grafted = raw.with_name(f"{raw.stem}.grafted{raw.suffix}")
    with open(grafted, "wb") as g, open(raw, "rb") as r:
        g.write(header)
        shutil.copyfileobj(r, g)
    return grafted
