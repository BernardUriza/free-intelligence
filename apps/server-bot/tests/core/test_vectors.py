"""The facts embedder: fi-core's SentenceTransformersEmbedder on MiniLM, one per process."""

from __future__ import annotations

from persona_core.vectors import EMBEDDING_DIM, MODEL_NAME, get_embedding_model


def test_singleton_and_configuration():
    a = get_embedding_model()
    assert a is get_embedding_model()
    assert a.model_name == MODEL_NAME
    assert a.normalize is True


def test_constants_match_model_name():
    """A swap to a 768d model must fail here, not in pgvector (VECTOR(384) in postgres_schema.sql)."""
    assert MODEL_NAME == "all-MiniLM-L6-v2"
    assert EMBEDDING_DIM == 384
