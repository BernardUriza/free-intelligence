"""DEPRECATED — re-exports from ``fi_core.rag``.

This module used to host the chunking algorithm directly. As of 2026-05-19
the canonical home is the ``fi-core`` package (``apps/packages/fi-core``).
The 220-line implementation that lived here was extracted verbatim, and
both AURITY and the Insult discord-bot now import from ``fi_core.rag``.

Why this file still exists:
- Backwards compatibility for any forgotten import path. Imports keep
  working without a hard break.
- An import-time DeprecationWarning surfaces the migration so the next
  reader knows to update.

DO NOT add new code here. Edit ``apps/packages/fi-core/fi_core/rag/chunking.py``
instead — that's the single source of truth that AURITY, fi-monitor, and
Insult all share.
"""

from __future__ import annotations

import warnings

from fi_core.rag import (
    ChunkConfig,
    ChunkingStrategy,
    chunk_by_fixed_size,
    chunk_by_paragraphs,
    chunk_by_sentences,
    chunk_document,
    estimate_tokens,
)

warnings.warn(
    "backend.services.document.services.chunking_strategy is deprecated. "
    "Import from `fi_core.rag` instead (apps/packages/fi-core).",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = [
    "ChunkConfig",
    "ChunkingStrategy",
    "chunk_by_fixed_size",
    "chunk_by_paragraphs",
    "chunk_by_sentences",
    "chunk_document",
    "estimate_tokens",
]
