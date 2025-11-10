"""WebM Header Grafting for RecordRTC Chunk Repair.

Card: AUR-PROMPT-3.4
Created: 2025-11-09

Problem:
- RecordRTC chunks > 0 arrive as raw Opus (no EBML header)
- FFmpeg fails: "EBML header parsing failed"

Solution:
- Extract header from chunk_0.webm (has EBML)
- Graft header onto raw chunks before ffmpeg decode

File: backend/workers/webm_graft.py
"""

from __future__ import annotations

import shutil
from pathlib import Path

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
    """Extract WebM header (everything before first Cluster element)."""
    idx = webm_bytes.find(EBML_CLUSTER_ID)
    if idx == -1:
        # Header till first cluster unknown; keep a safe cap
        return webm_bytes[: min(len(webm_bytes), 8192)]
    return webm_bytes[:idx]


def _candidate_chunk0_paths(sess_dir: Path) -> list[Path]:
    """Return candidate paths for chunk 0 (supports multiple naming)."""
    # Soporta 0.webm, chunk_0.webm y variantes grafted
    names = ["0.webm", "chunk_0.webm", "0.grafted.webm", "chunk_0.grafted.webm"]
    return [sess_dir / n for n in names]


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
