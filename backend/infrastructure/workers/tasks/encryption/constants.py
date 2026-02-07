"""Encryption constants and configuration.

AES-GCM-256 parameters following NIST SP 800-38D recommendations.

Author: Bernard Uriza Orozco + Claude Code
Created: 2026-02-02 (Extracted from encryption_worker.py)
Card: Infrastructure Modularization - Quick Wins (Rhea Moon)
"""

from typing import Final

# ═══════════════════════════════════════════════════════════════════
# AES-GCM-256 Parameters (NIST SP 800-38D)
# ═══════════════════════════════════════════════════════════════════

DEK_SIZE_BYTES: Final[int] = 32  # 256 bits
IV_SIZE_BYTES: Final[int] = 12  # 96 bits (recommended for GCM)
GCM_TAG_SIZE_BYTES: Final[int] = 16  # 128 bits authentication tag

# ═══════════════════════════════════════════════════════════════════
# HDF5 Schema Configuration
# ═══════════════════════════════════════════════════════════════════

CRYPTO_SCHEMA_VERSION: Final[str] = "v1"
CRYPTO_BASE_PATH: Final[str] = f"/crypto/{CRYPTO_SCHEMA_VERSION}"

# ═══════════════════════════════════════════════════════════════════
# Large File Chunking Configuration (FI-CORE-CRYPTO-15)
# ═══════════════════════════════════════════════════════════════════

CHUNK_SIZE_THRESHOLD_MB: Final[int] = 500  # Files > 500MB get chunked
CHUNK_DURATION_SECONDS: Final[int] = 60  # 60 second audio chunks
CHUNK_SIZE_BYTES: Final[int] = 50 * 1024 * 1024  # 50MB per chunk fallback

# ═══════════════════════════════════════════════════════════════════
# Default Encryption Targets (Template Patterns)
# ═══════════════════════════════════════════════════════════════════

# These will be formatted with session_id at runtime
DEFAULT_TARGET_PATTERNS: Final[list[str]] = [
    # Task-based schema (NEW - since 2025-11-14)
    "/sessions/{session_id}/tasks/TRANSCRIPTION/full_audio.webm",
    "/sessions/{session_id}/tasks/TRANSCRIPTION/webspeech_final",
    "/sessions/{session_id}/tasks/TRANSCRIPTION/full_transcription",
    "/sessions/{session_id}/tasks/DIARIZATION/segments",
    "/sessions/{session_id}/tasks/SOAP_GENERATION/soap_note",
    # Legacy schema (OLD - kept for backward compatibility)
    "/audio/full_audio",
    "/audio/raw",
    "/transcriptions",
    "/transcript",
    "/soap/note",
    "/soap",
]
