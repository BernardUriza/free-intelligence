"""Tests for insult.core.vectors — embedding model only.

Post-PG migration: the FTS5 + sqlite-vec hybrid is gone. Vector storage
now lives in pgvector (Postgres) and search is pure cosine similarity.
DB-touching tests are skipped pending a real-Postgres or asyncpg-pool
fixture (PG-5i); only the local-only EmbeddingModel surface is covered
here.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from insult.core.vectors import EMBEDDING_DIM, MODEL_NAME, EmbeddingModel, get_embedding_model


class TestEmbeddingModel:
    @patch("insult.core.vectors.EmbeddingModel._ensure_model")
    def test_embed_returns_correct_dim(self, _mock_ensure):
        """embed() should return a list of floats with EMBEDDING_DIM dimensions."""
        model = EmbeddingModel()
        fake_vector = [0.1] * EMBEDDING_DIM
        mock_st_model = MagicMock()
        mock_st_model.encode = MagicMock(return_value=_FakeArray(fake_vector))
        model._model = mock_st_model

        out = model.embed("hello world")
        assert isinstance(out, list)
        assert len(out) == EMBEDDING_DIM
        assert all(isinstance(x, float) for x in out)

    @patch("insult.core.vectors.EmbeddingModel._ensure_model")
    def test_embed_batch_handles_empty(self, _mock_ensure):
        """embed_batch([]) short-circuits and returns []; never loads the model."""
        model = EmbeddingModel()
        out = model.embed_batch([])
        assert out == []

    def test_singleton_get_embedding_model_returns_same_instance(self):
        """get_embedding_model() is a module-level singleton — two calls
        return the same object so the heavy model load only happens once."""
        a = get_embedding_model()
        b = get_embedding_model()
        assert a is b

    def test_constants_match_model_name(self):
        """The dim constant must match the documented model. Hardcoded check
        so a future swap to a 768d model fails loudly here rather than
        silently breaking pgvector schema (VECTOR(384) in postgres_schema.sql)."""
        assert MODEL_NAME == "all-MiniLM-L6-v2"
        assert EMBEDDING_DIM == 384


class _FakeArray:
    """Minimal numpy-array stub for the encode() return value."""

    def __init__(self, data: list[float]):
        self._data = data

    def tolist(self) -> list[float]:
        return self._data
