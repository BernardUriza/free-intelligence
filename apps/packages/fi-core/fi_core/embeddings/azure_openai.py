"""Reference :class:`fi_core.rag.protocols.Embedder` backed by Azure OpenAI.

This module provides ``AzureOpenAIEmbedder``, a thin wrapper around the
``openai`` SDK's ``AsyncAzureOpenAI`` client that satisfies fi-core's
``Embedder`` Protocol (``async def embed(self, text: str) -> list[float]``).

Origin: extracted from the discord-bot ``insult.core.deep_memory``
module (v3.9.60, refined in DM-5). The original embedded the same
class inside the bot's RAG module and read Azure credentials from
process environment variables inline. This extraction strips that
implicit-environment coupling: **callers must provide credentials
explicitly** via constructor args. fi-core does not read environment
variables — the consumer (discord-bot, insult-runner, AURITY, your
script) is responsible for sourcing config however it likes.

Optional dependency: requires the ``openai`` SDK. Install via the
``embeddings-azure`` extra::

    pip install 'fi-core[embeddings-azure]'

Failure semantics follow the ``Embedder`` Protocol contract: this
implementation raises on any failure path (empty input, missing config,
SDK error, dimension mismatch). It never returns empty / zero vectors
silently — that's a footgun the Protocol explicitly forbids.
"""

from __future__ import annotations

try:
    from openai import AsyncAzureOpenAI
except ImportError as e:  # pragma: no cover - exercised only when extra is missing
    raise ImportError(
        "fi_core.embeddings.azure_openai requires the openai SDK. "
        "Install via: pip install 'fi-core[embeddings-azure]'"
    ) from e


# Default output dimension for Azure OpenAI's ``text-embedding-ada-002``
# deployment. Override via the ``dim`` constructor arg if you point the
# embedder at a different model (e.g. ``text-embedding-3-small`` is also
# 1536, but ``text-embedding-3-large`` is 3072).
_ADA_002_DIM = 1536

# Conservative default; callers should pin the api_version their Azure
# deployment supports. 2024-02-01 is the GA version for ada-002.
_DEFAULT_API_VERSION = "2024-02-01"


class EmbeddingDimensionError(RuntimeError):
    """Azure returned a vector whose dim doesn't match the embedder's ``dim``.

    Raised by :meth:`AzureOpenAIEmbedder.embed` instead of silently
    returning the wrong-sized vector. A dimension mismatch is almost
    always a deployment misconfiguration (someone pointed the deployment
    name at ``text-embedding-3-large`` which is 3072 dims while the
    consumer expected 1536) and should fail loud, not corrupt the
    vector index downstream.
    """


class AzureOpenAIEmbedder:
    """:class:`fi_core.rag.protocols.Embedder` implementation for Azure OpenAI.

    Implements the structural contract
    (``async def embed(self, text: str) -> list[float]``) defined in
    :mod:`fi_core.rag.protocols`. The Protocol is ``@runtime_checkable``
    so ``isinstance(emb, Embedder)`` returns ``True`` without inheritance.

    Holds endpoint/key/deployment as instance state and reuses the
    ``AsyncAzureOpenAI`` client across calls — construct one embedder
    per worker, not per call, to avoid re-opening the HTTP connection
    pool on each embed.

    All configuration is explicit via constructor args. The caller is
    responsible for sourcing values from environment variables, a
    secrets manager, or a config object — fi-core does not read the
    environment.

    Parameters
    ----------
    api_key:
        Azure OpenAI API key. Required.
    endpoint:
        Azure OpenAI endpoint URL (e.g.
        ``https://my-account.openai.azure.com``). Trailing slash is
        trimmed. Required.
    deployment:
        Name of the deployed embedding model in your Azure account
        (NOT the model name — the deployment name you configured in
        Azure AI Studio). Required.
    api_version:
        Azure OpenAI API version string. Defaults to ``2024-02-01``,
        the GA version compatible with ``text-embedding-ada-002``.
    dim:
        Expected output vector dimension. Defaults to 1536 (ada-002 /
        text-embedding-3-small). Set to 3072 for text-embedding-3-large.
        :meth:`embed` raises :class:`EmbeddingDimensionError` if the
        deployment returns a vector with a different size.
    """

    def __init__(
        self,
        *,
        api_key: str,
        endpoint: str,
        deployment: str,
        api_version: str = _DEFAULT_API_VERSION,
        dim: int = _ADA_002_DIM,
    ) -> None:
        if not api_key:
            raise ValueError("AzureOpenAIEmbedder: api_key is required")
        if not endpoint:
            raise ValueError("AzureOpenAIEmbedder: endpoint is required")
        if not deployment:
            raise ValueError("AzureOpenAIEmbedder: deployment is required")
        if dim <= 0:
            raise ValueError("AzureOpenAIEmbedder: dim must be positive")
        self.api_key = api_key
        self.endpoint = endpoint.rstrip("/")
        self.deployment = deployment
        self.api_version = api_version
        self._dim = dim
        self._client: AsyncAzureOpenAI | None = None  # lazy

    @property
    def dim(self) -> int:
        """Expected output vector dimension for this embedder."""
        return self._dim

    def _get_client(self) -> AsyncAzureOpenAI:
        """Lazily build the Azure client. Reused across embed() calls."""
        if self._client is None:
            self._client = AsyncAzureOpenAI(
                azure_endpoint=self.endpoint,
                api_key=self.api_key,
                api_version=self.api_version,
            )
        return self._client

    async def embed(self, text: str) -> list[float]:
        """Return a ``self.dim``-element vector for ``text``.

        Raises
        ------
        ValueError
            If ``text`` is empty or whitespace-only.
        EmbeddingDimensionError
            If the deployment returns a wrong-sized vector (deployment
            misconfiguration).

        Other exceptions from the openai SDK (auth, rate-limit, timeout,
        etc.) are surfaced unwrapped so the caller can branch on
        ``openai.RateLimitError`` / ``openai.APITimeoutError`` directly
        without parsing strings.
        """
        if not text or not text.strip():
            raise ValueError("AzureOpenAIEmbedder.embed: text must be non-empty")
        client = self._get_client()
        resp = await client.embeddings.create(model=self.deployment, input=text)
        vec = resp.data[0].embedding
        if len(vec) != self._dim:
            raise EmbeddingDimensionError(
                f"Expected {self._dim}-dim vector, got {len(vec)} from "
                f"deployment '{self.deployment}'"
            )
        return list(vec)
