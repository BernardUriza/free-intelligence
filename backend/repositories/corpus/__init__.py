"""Corpus repository package.

Re-exports the ``CorpusRepository`` facade so that consumers can
import from ``backend.repositories.corpus`` directly.
"""

from __future__ import annotations

from .repository import CorpusRepository

__all__ = ["CorpusRepository"]
