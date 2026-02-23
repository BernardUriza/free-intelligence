"""Backward-compatibility shim for ``CorpusRepository``.

The implementation has been refactored into the
``backend.repositories.corpus`` package.  This module re-exports the
class so that existing ``from backend.repositories.corpus_repository
import CorpusRepository`` statements continue to work.
"""

from __future__ import annotations

from .corpus import CorpusRepository

__all__ = ["CorpusRepository"]
