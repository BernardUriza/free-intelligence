"""Reference Embedder implementation backed by a local sentence-transformers model.

This module provides ``SentenceTransformersEmbedder``, a reference implementation
of the ``fi_core.rag.protocols.Embedder`` protocol that loads a HuggingFace
sentence-transformers model into the local process and returns embedding vectors
for input text.

Scope and non-scope:
  - This implementation is intentionally simple: it embeds text with a locally
    loaded model. No HTTP transport, no GPU service discovery, no remote tunnel.
  - AURITY's production deployment historically wrapped a Cloudflare-tunneled
    GPU service (see ``apps/fi-monitor/rag_service``) so the model lived on a
    different machine than the consumer. That transport is AURITY-specific and
    stays in AURITY — fi-core only ships the local-loader form.
  - Consumers that want the remote-transport form should compose their own
    Embedder around an HTTP client; the Protocol surface is intentionally small.

Optional dependency:
  Install with ``pip install 'fi-core[embeddings-st]'`` (or directly
  install ``sentence-transformers`` and ``torch``). Importing this module
  without the deps raises ImportError immediately with installation hint.

Author: Bernard Uriza Orozco
"""

from __future__ import annotations

import asyncio
import threading

try:
    from sentence_transformers import SentenceTransformer
    import torch
except ImportError as e:
    raise ImportError(
        "fi_core.embeddings.sentence_transformers requires sentence-transformers and torch. "
        "Install via: pip install 'fi-core[embeddings-st]'"
    ) from e


DEFAULT_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


def _auto_device() -> str:
    """Pick the best locally available device: cuda > mps > cpu."""
    if torch.cuda.is_available():
        return "cuda"
    # ``torch.backends.mps.is_available`` may not exist on every torch build.
    mps_backend = getattr(torch.backends, "mps", None)
    if mps_backend is not None and getattr(mps_backend, "is_available", lambda: False)():
        return "mps"
    return "cpu"


class SentenceTransformersEmbedder:
    """Local sentence-transformers Embedder.

    Implements ``fi_core.rag.protocols.Embedder``. The underlying model is
    loaded lazily on the first call to ``embed`` (or the first read of
    ``dim``) so that constructing the instance is cheap and import-safe —
    in particular, no GPU memory is allocated at construction time.

    The synchronous ``model.encode`` call is dispatched through
    ``asyncio.to_thread`` to avoid blocking the event loop.

    Args:
        model_name: HuggingFace model identifier. Defaults to
            ``sentence-transformers/all-MiniLM-L6-v2`` (384-dim).
        device: Explicit device string (``"cpu"`` / ``"cuda"`` / ``"mps"``).
            ``None`` (default) auto-detects via ``torch.cuda.is_available``
            and ``torch.backends.mps.is_available``.

    ``dim`` triggers lazy load just like ``embed`` does — reading it before
    the first ``embed`` call will load the model. If you need the dimension
    without paying for a load, hard-code it from the model card.
    """

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL_NAME,
        device: str | None = None,
        *,
        query_prefix: str = "",
        passage_prefix: str = "",
        normalize: bool = False,
    ) -> None:
        self._model_name = model_name
        self._device = device if device is not None else _auto_device()
        self._model: SentenceTransformer | None = None
        self._lock = threading.Lock()
        self.query_prefix = query_prefix
        self.passage_prefix = passage_prefix
        self.normalize = normalize

    def _ensure_loaded(self) -> SentenceTransformer:
        """Load the model on first use. Idempotent."""
        if self._model is None:
            with self._lock:
                if self._model is None:
                    self._model = SentenceTransformer(self._model_name, device=self._device)
        return self._model

    @property
    def model_name(self) -> str:
        """The HuggingFace model identifier this embedder was constructed with."""
        return self._model_name

    @property
    def device(self) -> str:
        """The resolved device string (after auto-detection if device=None)."""
        return self._device

    @property
    def dim(self) -> int:
        """Output dimension of the loaded model.

        Triggers a lazy load if the model has not been loaded yet (consistent
        with ``embed``). Returns the value from
        ``SentenceTransformer.get_sentence_embedding_dimension()``.

        Raises:
            RuntimeError: if the underlying model reports ``None`` for its
                embedding dimension (some pooling-less models do this — we
                refuse to silently return a sentinel because dimension
                mismatch downstream is a footgun).
        """
        model = self._ensure_loaded()
        raw = model.get_sentence_embedding_dimension()
        if raw is None:
            raise RuntimeError(
                f"Model {self._model_name!r} reports no embedding dimension. "
                "Pass a model with a pooling layer (most sentence-transformers "
                "models qualify) or override the dim explicitly."
            )
        return int(raw)

    async def embed(self, text: str) -> list[float]:
        """Return the embedding vector for ``text`` as a list of floats.

        The first call loads the model (potentially slow — model download
        on cold cache, GPU memory allocation if device != "cpu"). Subsequent
        calls reuse the loaded model.

        ``model.encode`` is CPU/GPU bound; it runs through
        ``asyncio.to_thread`` so it does not block the event loop.

        Raises whatever the underlying ``model.encode`` raises (e.g.,
        ``RuntimeError`` for CUDA OOM, ``ValueError`` for malformed input).
        """
        return await asyncio.to_thread(self._encode, text)

    async def embed_query(self, text: str) -> list[float]:
        """Embed a search text with `query_prefix` (e5 needs `query: `)."""
        return await asyncio.to_thread(self._encode, self.query_prefix + text)

    async def embed_passage(self, text: str) -> list[float]:
        """Embed a stored chunk with `passage_prefix` (e5 needs `passage: `)."""
        return await asyncio.to_thread(self._encode, self.passage_prefix + text)

    def _encode(self, text: str) -> list[float]:
        vector = self._ensure_loaded().encode(
            text,
            convert_to_numpy=True,
            show_progress_bar=False,
            normalize_embeddings=self.normalize,
        )
        return vector.tolist()
