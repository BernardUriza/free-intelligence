"""Global mutable state for RAG Service."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

_model: SentenceTransformer | None = None
_document_store: dict[str, dict] = {}
_ground_truth_store: dict[str, list[dict[str, Any]]] = {}
