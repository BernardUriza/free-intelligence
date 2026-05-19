"""Tests for fi_core.embeddings.azure_openai.AzureOpenAIEmbedder.

Mock-only — no real network calls to Azure. The contract pinned here:

1. Satisfies the ``Embedder`` Protocol (``@runtime_checkable``).
2. Constructor requires explicit credentials (no env-var reading).
3. ``embed`` returns ``list[float]`` of the configured dimension.
4. ``embed`` raises on empty input.
5. Dimension mismatch raises ``EmbeddingDimensionError``.
6. SDK errors propagate (Protocol contract: never swallow failures).

The whole module is skipped if the ``openai`` SDK isn't installed (the
``embeddings-azure`` extra is opt-in).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

pytest.importorskip("openai")

from fi_core.embeddings.azure_openai import (  # noqa: E402
    AzureOpenAIEmbedder,
    EmbeddingDimensionError,
)
from fi_core.rag.protocols import Embedder  # noqa: E402


def _fake_response(vector: list[float]) -> MagicMock:
    """Build a MagicMock that mimics ``openai`` embeddings.create response."""
    datum = MagicMock()
    datum.embedding = vector
    resp = MagicMock()
    resp.data = [datum]
    return resp


def _make_embedder(*, dim: int = 4) -> AzureOpenAIEmbedder:
    """Construct an embedder with throwaway test credentials.

    ``dim`` is kept tiny (default 4) so tests stay readable. The real
    deployment would return 1536-dim vectors but the contract is the
    same regardless of size.
    """
    return AzureOpenAIEmbedder(
        api_key="test-key",
        endpoint="https://test.openai.azure.com",
        deployment="test-deployment",
        api_version="2024-02-01",
        dim=dim,
    )


def _install_fake_client(embedder: AzureOpenAIEmbedder, create_mock: AsyncMock) -> None:
    """Wire a fake AsyncAzureOpenAI client into the embedder.

    Bypasses ``_get_client`` lazy construction by populating
    ``embedder._client`` directly with a structurally-compatible mock.
    """
    fake_client = MagicMock()
    fake_client.embeddings = MagicMock()
    fake_client.embeddings.create = create_mock
    embedder._client = fake_client


def test_satisfies_embedder_protocol():
    """AzureOpenAIEmbedder is structurally a fi_core.rag.protocols.Embedder."""
    emb = _make_embedder()
    assert isinstance(emb, Embedder)


def test_constructor_requires_api_key():
    with pytest.raises(ValueError, match="api_key"):
        AzureOpenAIEmbedder(
            api_key="",
            endpoint="https://test.openai.azure.com",
            deployment="test-deployment",
        )


def test_constructor_requires_endpoint():
    with pytest.raises(ValueError, match="endpoint"):
        AzureOpenAIEmbedder(
            api_key="test-key",
            endpoint="",
            deployment="test-deployment",
        )


def test_constructor_requires_deployment():
    with pytest.raises(ValueError, match="deployment"):
        AzureOpenAIEmbedder(
            api_key="test-key",
            endpoint="https://test.openai.azure.com",
            deployment="",
        )


def test_constructor_rejects_non_positive_dim():
    with pytest.raises(ValueError, match="dim"):
        AzureOpenAIEmbedder(
            api_key="test-key",
            endpoint="https://test.openai.azure.com",
            deployment="test-deployment",
            dim=0,
        )


def test_constructor_strips_trailing_slash_from_endpoint():
    emb = AzureOpenAIEmbedder(
        api_key="test-key",
        endpoint="https://test.openai.azure.com/",
        deployment="test-deployment",
    )
    assert emb.endpoint == "https://test.openai.azure.com"


def test_dim_property_defaults_to_1536():
    emb = AzureOpenAIEmbedder(
        api_key="test-key",
        endpoint="https://test.openai.azure.com",
        deployment="test-deployment",
    )
    assert emb.dim == 1536


def test_dim_property_reflects_constructor_arg():
    emb = _make_embedder(dim=3072)
    assert emb.dim == 3072


async def test_embed_returns_vector_from_sdk_response():
    emb = _make_embedder(dim=4)
    expected = [0.1, 0.2, 0.3, 0.4]
    create = AsyncMock(return_value=_fake_response(expected))
    _install_fake_client(emb, create)

    result = await emb.embed("hello world")

    assert result == expected
    assert isinstance(result, list)
    assert all(isinstance(v, float) for v in result)
    create.assert_awaited_once_with(model="test-deployment", input="hello world")


async def test_embed_raises_on_empty_text():
    emb = _make_embedder()
    with pytest.raises(ValueError, match="non-empty"):
        await emb.embed("")


async def test_embed_raises_on_whitespace_only_text():
    emb = _make_embedder()
    with pytest.raises(ValueError, match="non-empty"):
        await emb.embed("   \n\t  ")


async def test_embed_raises_on_dimension_mismatch():
    """Deployment misconfig (wrong model size) must fail loud, not corrupt index."""
    emb = _make_embedder(dim=4)
    # Configured for dim=4 but Azure returned 6 — typical of swapping
    # ada-002 (1536) for text-embedding-3-large (3072) without updating
    # the consumer side.
    create = AsyncMock(return_value=_fake_response([0.1, 0.2, 0.3, 0.4, 0.5, 0.6]))
    _install_fake_client(emb, create)

    with pytest.raises(EmbeddingDimensionError, match="Expected 4-dim"):
        await emb.embed("hello")


async def test_embed_propagates_sdk_errors():
    """Per Embedder Protocol: implementations must raise on failure, not swallow."""
    emb = _make_embedder()

    class FakeRateLimit(Exception):
        pass

    create = AsyncMock(side_effect=FakeRateLimit("429 too many requests"))
    _install_fake_client(emb, create)

    with pytest.raises(FakeRateLimit, match="429"):
        await emb.embed("hello")


async def test_embed_reuses_client_across_calls():
    """Lazy client is cached on the instance to avoid HTTP-pool re-init."""
    emb = _make_embedder(dim=4)
    create = AsyncMock(return_value=_fake_response([0.1, 0.2, 0.3, 0.4]))
    _install_fake_client(emb, create)
    cached_client = emb._client

    await emb.embed("first")
    await emb.embed("second")

    assert emb._client is cached_client
    assert create.await_count == 2
