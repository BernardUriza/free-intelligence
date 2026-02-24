"""Pure extraction helpers for session HDF5 data.

Stateless utility functions that extract structured information from
HDF5 groups.  They accept ``h5py`` objects and return plain Python
values — no file I/O, no repository coupling.

Author: Bernard Uriza Orozco
"""

from __future__ import annotations

import json
import re
from typing import Any

import h5py
from backend.utils.common.logging.logger import get_logger

logger = get_logger(__name__)

# Sentinel value when a creation timestamp cannot be determined.
_EPOCH_FALLBACK = "2000-01-01T00:00:00+00:00"

# Regex patterns for doctor name extraction from diarization text.
_DOCTOR_NAME_PATTERNS: list[re.Pattern[str]] = [
    re.compile(
        r"(?:soy el|mi nombre es|me llamo)\s+doctor[a]?\s+"
        r"([A-Za-zÁÉÍÓÚáéíóúÑñ]+)",
        re.IGNORECASE,
    ),
    re.compile(
        r"doctor[a]?\s+([A-Za-zÁÉÍÓÚáéíóúÑñ]{3,})",
        re.IGNORECASE,
    ),
]

# Words that look like names but are actually noise.
_COMMON_WORDS: frozenset[str] = frozenset(
    {"que", "como", "por", "con", "para", "los", "las", "del", "una", "uno"}
)


def extract_session_created_at(tasks: Any) -> str:
    """Derive a creation timestamp from session tasks.

    Priority order:
        1. TRANSCRIPTION metadata ``created_at``
        2. First chunk (``chunk_0``) ``created_at``
        3. Fallback to epoch constant

    Args:
        tasks: HDF5 group containing task sub-groups.

    Returns:
        ISO-8601 timestamp string.
    """
    if "TRANSCRIPTION" not in tasks:
        return _EPOCH_FALLBACK

    trans_task = tasks["TRANSCRIPTION"]

    # 1 — metadata dataset
    if "metadata" in trans_task:
        meta_ds = trans_task["metadata"]
        if isinstance(meta_ds, h5py.Dataset):
            meta_json = meta_ds[()].decode("utf-8")
            meta = json.loads(meta_json)
            created = meta.get("created_at")
            if created:
                return str(created)

    # 2 — first chunk
    if "chunks" in trans_task and "chunk_0" in trans_task["chunks"]:
        chunk_0 = trans_task["chunks"]["chunk_0"]
        if "created_at" in chunk_0:
            created_at_ds = chunk_0["created_at"]
            if isinstance(created_at_ds, h5py.Dataset):
                return created_at_ds[()].decode("utf-8")

    return _EPOCH_FALLBACK


def extract_transcription_details(
    tasks: Any,
    session_id: str,
) -> tuple[int, float, str]:
    """Extract chunk count, total duration, and a text preview.

    Args:
        tasks: HDF5 group containing task sub-groups.
        session_id: Used only for warning-level logging.

    Returns:
        ``(chunk_count, duration_seconds, preview_text)``
    """
    if "TRANSCRIPTION" not in tasks:
        return (0, 0.0, "")

    trans_task = tasks["TRANSCRIPTION"]
    if "chunks" not in trans_task:
        return (0, 0.0, "")

    chunks_group = trans_task["chunks"]
    chunk_count: int = len(chunks_group.keys())
    if chunk_count == 0:
        return (0, 0.0, "")

    duration_seconds = 0.0
    preview = ""

    try:
        # Preview from the first chunk's transcript
        if "chunk_0" in chunks_group:
            chunk_0 = chunks_group["chunk_0"]
            if "transcript" in chunk_0:
                transcript_ds = chunk_0["transcript"]
                if isinstance(transcript_ds, h5py.Dataset):
                    transcript = transcript_ds[()].decode("utf-8")
                    preview = transcript[:200]

        # Accumulate durations across all chunks
        for i in range(chunk_count):
            chunk_key = f"chunk_{i}"
            if chunk_key in chunks_group:
                chunk = chunks_group[chunk_key]
                if "duration" in chunk:
                    duration_seconds += float(chunk["duration"][()])

    except Exception as e:
        logger.warning("SKIP_CHUNK_DATA", session_id=session_id, error=str(e))

    return (chunk_count, duration_seconds, preview)


def extract_doctor_name_from_diarization(
    tasks: Any,
    session_id: str,
) -> str:
    """Search early diarization segments for a doctor name.

    Inspects the first 5 segments for patterns such as
    *"soy el doctor García"* or *"doctora López"*.

    Args:
        tasks: HDF5 group containing task sub-groups.
        session_id: Used only for warning-level logging.

    Returns:
        Capitalised doctor name, or empty string if not found.
    """
    if "DIARIZATION" not in tasks:
        return ""

    diar_task = tasks["DIARIZATION"]
    if "segments" not in diar_task:
        return ""

    segments = diar_task["segments"]

    try:
        for seg_key in list(segments.keys())[:5]:
            segment = segments[seg_key]
            if "text" not in segment:
                continue

            text_ds = segment["text"]
            if not isinstance(text_ds, h5py.Dataset):
                continue

            text = text_ds[()].decode("utf-8").lower()

            for pattern in _DOCTOR_NAME_PATTERNS:
                match = pattern.search(text)
                if match:
                    name = match.group(1).capitalize()
                    if name.lower() not in _COMMON_WORDS:
                        return name

    except Exception as e:
        logger.warning("SKIP_NAME_EXTRACTION", session_id=session_id, error=str(e))

    return ""
