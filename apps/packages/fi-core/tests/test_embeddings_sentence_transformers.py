"""Tests for fi_core.embeddings.sentence_transformers.SentenceTransformersEmbedder.

Skips the entire module when ``sentence-transformers`` is not installed
(via ``pytest.importorskip``). When deps are present, exercises:

  - Protocol conformance via ``isinstance(..., Embedder)``.
  - Lazy-load contract: ``SentenceTransformer`` constructor is NOT called
    at ``__init__``, but is called exactly once on the first ``embed``.
  - ``dim`` triggers lazy load too (consistent with ``embed``).
  - Error propagation when ``model.encode`` raises.
  - Heavy end-to-end smoke test that actually loads
    ``all-MiniLM-L6-v2`` on CPU and verifies the 384-dim output.
    Marked ``@pytest.mark.slow`` so it can be skipped from the fast path
    via ``pytest -m "not slow"``.

The heavy test downloads ~80MB on first run and is cached by HuggingFace
afterwards. It is a deliberate choice to keep it in-suite — the contract
"this thing produces 384-dim vectors with the default model" is the
whole reason this class exists.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

# Skip the whole module if the optional dep is missing.
pytest.importorskip("sentence_transformers")
pytest.importorskip("torch")

from fi_core.embeddings.sentence_transformers import (  # noqa: E402
    DEFAULT_MODEL_NAME,
    SentenceTransformersEmbedder,
)
from fi_core.rag.protocols import Embedder  # noqa: E402


# ============================================================
# Protocol conformance
# ============================================================


def test_satisfies_embedder_protocol():
    """SentenceTransformersEmbedder structurally matches the Embedder protocol."""
    emb = SentenceTransformersEmbedder()
    assert isinstance(emb, Embedder)


# ============================================================
# Lazy loading contract
# ============================================================


def test_init_does_not_load_model():
    """Constructing the embedder must NOT invoke SentenceTransformer()."""
    with patch(
        "fi_core.embeddings.sentence_transformers.SentenceTransformer"
    ) as mock_st:
        emb = SentenceTransformersEmbedder(model_name="some/model", device="cpu")
        assert mock_st.call_count == 0
        # Sanity: instance attributes are set without touching the model.
        assert emb.model_name == "some/model"
        assert emb.device == "cpu"


@pytest.mark.asyncio
async def test_first_embed_triggers_load_exactly_once():
    """Calling embed twice should construct SentenceTransformer exactly once."""
    fake_model = MagicMock()
    fake_model.encode.return_value = _np_array([0.1, 0.2, 0.3])
    fake_model.get_sentence_embedding_dimension.return_value = 3

    with patch(
        "fi_core.embeddings.sentence_transformers.SentenceTransformer",
        return_value=fake_model,
    ) as mock_st:
        emb = SentenceTransformersEmbedder(model_name="fake/model", device="cpu")
        assert mock_st.call_count == 0

        v1 = await emb.embed("hello")
        assert mock_st.call_count == 1
        assert v1 == [pytest.approx(0.1), pytest.approx(0.2), pytest.approx(0.3)]

        v2 = await emb.embed("world")
        assert mock_st.call_count == 1  # Still 1 — load was cached.
        assert v2 == [pytest.approx(0.1), pytest.approx(0.2), pytest.approx(0.3)]


def test_dim_triggers_lazy_load():
    """Reading .dim before any embed call still triggers the lazy load.

    Documents the contract: .dim is consistent with .embed — both load on
    first access. Callers that need the dimension without paying for a load
    should hard-code it from the model card.
    """
    fake_model = MagicMock()
    fake_model.get_sentence_embedding_dimension.return_value = 384

    with patch(
        "fi_core.embeddings.sentence_transformers.SentenceTransformer",
        return_value=fake_model,
    ) as mock_st:
        emb = SentenceTransformersEmbedder()
        assert mock_st.call_count == 0
        assert emb.dim == 384
        assert mock_st.call_count == 1


# ============================================================
# Error propagation
# ============================================================


@pytest.mark.asyncio
async def test_encode_error_propagates():
    """Errors raised by model.encode must bubble up to the caller."""
    fake_model = MagicMock()
    fake_model.encode.side_effect = RuntimeError("simulated CUDA OOM")

    with patch(
        "fi_core.embeddings.sentence_transformers.SentenceTransformer",
        return_value=fake_model,
    ):
        emb = SentenceTransformersEmbedder(device="cpu")
        with pytest.raises(RuntimeError, match="simulated CUDA OOM"):
            await emb.embed("trigger failure")


# ============================================================
# Constructor surface
# ============================================================


def test_default_model_name():
    """Default model is the 384-dim MiniLM."""
    emb = SentenceTransformersEmbedder()
    assert emb.model_name == DEFAULT_MODEL_NAME == "sentence-transformers/all-MiniLM-L6-v2"


def test_explicit_device_overrides_auto():
    """Passing an explicit device skips auto-detection."""
    emb = SentenceTransformersEmbedder(device="cpu")
    assert emb.device == "cpu"


# ============================================================
# Heavy end-to-end (real model load) — marked slow
# ============================================================


@pytest.mark.slow
@pytest.mark.asyncio
async def test_real_model_produces_384_dim_vector():
    """Load all-MiniLM-L6-v2 on CPU, encode a short string, assert 384-dim list[float].

    First-run cost: ~80MB download + ~3-5s load. Cached afterwards.
    Run with: pytest -m slow tests/test_embeddings_sentence_transformers.py
    Skip with: pytest -m 'not slow'
    """
    emb = SentenceTransformersEmbedder(device="cpu")
    vector = await emb.embed("the quick brown fox")
    assert isinstance(vector, list)
    assert len(vector) == 384
    assert all(isinstance(x, float) for x in vector)
    # .dim should now agree with what we just measured.
    assert emb.dim == 384


# ============================================================
# Helpers
# ============================================================


def _np_array(values):
    """Minimal numpy.ndarray-like that supports .tolist() — used in mocks."""
    import numpy as np

    return np.array(values, dtype=float)
