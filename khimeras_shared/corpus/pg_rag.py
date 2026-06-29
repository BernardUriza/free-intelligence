"""Persona-neutral pgvector RAG primitives — the shared retrieval substrate.

Extracted from `personas/insult/core/deep_memory.py` (Etapa 3 demux físico,
2026-06-15) so the RAG capability stops living inside a persona. Both the
per-user memory (`deep_memory`, Insult) and the shared film-theory corpus
(`film_references`, consumed by Insult AND ALICE) sit on top of these:

- `AzureOpenAIEmbedder` — `fi_core.rag.Embedder` Protocol impl over Azure OpenAI
- `embed_text(text)` — back-compat convenience embed, None on failure
- `connect()` — one-shot asyncpg connection with the pgvector codec registered

Everything here is env-driven (AZURE_OPENAI_* + POSTGRES_URL) and imports NOTHING
from `personas.*` — that keeps `khimeras_shared` free of any persona dependency
(enforced by tests/arch/test_arch_import_boundaries.py::test_shared_never_imports_personas).
"""

from __future__ import annotations

import os

import asyncpg
import structlog

log = structlog.get_logger()

EMBEDDING_DIM = 1536
EMBEDDING_DEPLOYMENT = os.environ.get("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-ada-002")
EMBEDDING_API_VERSION = os.environ.get("AZURE_OPENAI_EMBEDDING_API_VERSION", "2024-02-01")


# ─── Embeddings ────────────────────────────────────────────────────────


class EmbeddingDimensionError(RuntimeError):
    """The Azure deployment returned a vector whose dim doesn't match EMBEDDING_DIM.

    Raised by `AzureOpenAIEmbedder.embed()` instead of silently returning
    None — the embedder Protocol contract is "raise on failure". A
    dimension mismatch is almost always a deployment misconfiguration
    (someone pointed the env var at `text-embedding-3-large` which is
    3072 dims) and should fail loud, not corrupt the index silently.
    """


class AzureOpenAIEmbedder:
    """`fi_core.rag.Embedder` Protocol implementation for Azure OpenAI.

    Implements the structural contract (`async def embed(self, text: str)
    -> list[float]`) defined in `fi_core.rag.protocols.Embedder`. Duck-
    typed: `isinstance(emb, Embedder)` returns True via @runtime_checkable.

    Holds endpoint/key/deployment as instance state and reuses the
    AsyncAzureOpenAI client across calls. Constructing one embedder
    per worker (rather than per call) avoids re-opening the HTTP
    connection pool for every embed.

    Configuration precedence: explicit constructor args > env vars >
    module defaults. Most consumers just call `AzureOpenAIEmbedder()`
    and let the env vars do the work — same env vars the discord-bot
    and persona-runner Container Apps already have set.
    """

    def __init__(
        self,
        *,
        endpoint: str | None = None,
        api_key: str | None = None,
        deployment: str | None = None,
        api_version: str | None = None,
    ) -> None:
        self.endpoint = (endpoint or os.environ.get("AZURE_OPENAI_ENDPOINT", "")).rstrip("/")
        self.api_key = api_key or os.environ.get("AZURE_OPENAI_KEY", "")
        self.deployment = deployment or EMBEDDING_DEPLOYMENT
        self.api_version = api_version or EMBEDDING_API_VERSION
        self._client: object | None = None  # lazy AsyncAzureOpenAI

    def _get_client(self):
        """Lazily build the Azure client. Reused across embed() calls."""
        if self._client is not None:
            return self._client
        if not self.endpoint or not self.api_key:
            raise RuntimeError(
                "AzureOpenAIEmbedder requires AZURE_OPENAI_ENDPOINT + AZURE_OPENAI_KEY (env vars or constructor args)"
            )
        from openai import AsyncAzureOpenAI

        self._client = AsyncAzureOpenAI(
            azure_endpoint=self.endpoint,
            api_key=self.api_key,
            api_version=self.api_version,
        )
        return self._client

    async def embed(self, text: str) -> list[float]:
        """Return a `EMBEDDING_DIM`-element vector for ``text``.

        Raises (per Protocol contract):
        - `ValueError` if ``text`` is empty / whitespace-only.
        - `RuntimeError` if endpoint/key aren't configured.
        - `EmbeddingDimensionError` if the deployment returns a
          wrong-sized vector (deployment misconfiguration).
        - Whatever the openai SDK raises (auth, rate-limit, etc.) —
          surfaced unwrapped so the caller can branch on `RateLimitError`,
          `APITimeoutError`, etc. without parsing strings.
        """
        if not text or not text.strip():
            raise ValueError("AzureOpenAIEmbedder.embed: text must be non-empty")
        client = self._get_client()
        resp = await client.embeddings.create(model=self.deployment, input=text)
        vec = resp.data[0].embedding
        if len(vec) != EMBEDDING_DIM:
            raise EmbeddingDimensionError(
                f"Expected {EMBEDDING_DIM}-dim vector, got {len(vec)} from deployment '{self.deployment}'"
            )
        return vec


# Module-level singleton built lazily on first use. Avoids paying the
# openai client construction cost on every embed_text() call.
_default_embedder: AzureOpenAIEmbedder | None = None


def _get_default_embedder() -> AzureOpenAIEmbedder:
    global _default_embedder
    if _default_embedder is None:
        _default_embedder = AzureOpenAIEmbedder()
    return _default_embedder


async def embed_text(text: str) -> list[float] | None:
    """Back-compat convenience: embed `text`, return None on failure.

    Pre-DM-5 callers used this function directly; it survives so the
    backfill script and the MCP tool don't have to change. New code
    should prefer constructing an `AzureOpenAIEmbedder` explicitly and
    handling its exceptions, which gives the caller real failure-mode
    granularity instead of a binary None / not-None.

    Catches and swallows all exceptions, logging each via structlog.
    Callers who need to distinguish auth-failure from rate-limit from
    dim-mismatch should use `AzureOpenAIEmbedder.embed` directly.
    """
    if not text or not text.strip():
        return None
    try:
        return await _get_default_embedder().embed(text)
    except Exception:
        log.exception("deep_memory_embed_failed", text_len=len(text))
        return None


# ─── Storage ───────────────────────────────────────────────────────────


async def connect() -> asyncpg.Connection | None:
    """One-shot asyncpg connection with the pgvector codec registered.

    Reads POSTGRES_URL from the environment; returns None when it isn't set
    or the connection fails, so every caller can treat absence-of-PG as a
    valid (empty) answer rather than an error.
    """
    url = os.environ.get("POSTGRES_URL")
    if not url:
        return None
    try:
        conn = await asyncpg.connect(url)
        # Register pgvector codec so we can pass/receive list[float] as
        # `vector` directly without manual cast strings.
        try:
            from pgvector.asyncpg import register_vector

            await register_vector(conn)
        except Exception:
            log.warning("deep_memory_pgvector_codec_register_failed")
        return conn
    except Exception:
        log.exception("deep_memory_pg_connect_failed")
        return None
