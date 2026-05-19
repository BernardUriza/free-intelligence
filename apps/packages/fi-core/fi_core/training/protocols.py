"""Training-side Protocols for fi_core.training.

The package ships reference implementations under
``fi_core.training.datasets``, ``fi_core.training.tokenizers``,
``fi_core.training.models``, and ``fi_core.training.trainers`` —
but the Protocols defined here are the integration surface a
downstream consumer (Robo-Poet, AURITY's training pipeline,
discord-bot's distillation experiments) must satisfy if it wants to
swap any layer.

V2 narrative: training is a utility surface, not a closed loop. The
patterns shipped by ``fi_core.persona`` are NOT derived from the
corpus a consumer trains on with this module — they are human-distilled
from observed production failure modes. ``fi_core.training`` ships the
pipes (datasets that read what ``fi_core.stores`` write, tokenizers,
a small GPT class, a PyTorch trainer); how a consumer uses them is
their own story.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from fi_core.rag.types import Chunk


@runtime_checkable
class DatasetReader(Protocol):
    """Read training chunks from a fi-core ``DocumentChunkStore`` backend.

    The training side reads what the production stores have already
    written; a ``DatasetReader`` is a thin async iterator that surfaces
    chunks one at a time so a trainer can stream them into a DataLoader
    without holding the whole corpus in RAM.

    Yields plain ``Chunk`` (text + source ref). Embeddings stored by the
    backend are NOT surfaced — for LM training you re-tokenize, and if
    your task wants embedding alignment you call your ``Embedder``
    fresh. This keeps the contract minimal and makes the reader
    embedding-method-agnostic.
    """

    async def read_chunks(
        self,
        namespace: str,
        *,
        limit: int | None = None,
    ) -> AsyncIterator[Chunk]:
        """Yield ``Chunk`` instances for ``namespace``.

        If ``limit`` is None, yield every chunk in the namespace. The
        ordering is implementation-defined but stable across calls on
        the same store snapshot.
        """
        ...

    async def count(self, namespace: str) -> int:
        """Return the number of chunks available in ``namespace``."""
        ...


@runtime_checkable
class Tokenizer(Protocol):
    """Text ↔ token-id codec for the training and generation side.

    ``vocab_size`` is the size of the token-id space the model will
    embed. ``encode`` and ``decode`` are the round-trip pair. The
    Protocol is intentionally minimal — the heavy machinery (merges,
    pre-tokenization rules, special tokens) is an implementation detail
    of the concrete tokenizer.
    """

    @property
    def vocab_size(self) -> int:
        """Size of the token id space (max id + 1)."""
        ...

    def encode(self, text: str) -> list[int]:
        """Encode ``text`` to a list of token ids."""
        ...

    def decode(self, ids: list[int]) -> str:
        """Decode token ids back to text. Reverse of :meth:`encode`."""
        ...


@runtime_checkable
class GenerationModel(Protocol):
    """A model that can generate text autoregressively given a prompt.

    Concrete impls in ``fi_core.training.models`` (e.g. ``TinyGPT``)
    satisfy this Protocol. Consumers that only need generation (not
    training) can depend on this Protocol alone.
    """

    def generate(
        self,
        prompt_ids: list[int],
        *,
        max_new_tokens: int = 200,
        temperature: float = 0.8,
        top_k: int | None = 40,
        top_p: float | None = 0.95,
        repetition_penalty: float = 1.0,
    ) -> list[int]:
        """Generate up to ``max_new_tokens`` ids continuing ``prompt_ids``.

        Returns the FULL sequence (prompt + new tokens), not just the
        new ones, so callers can slice as needed.
        """
        ...


@runtime_checkable
class Trainer(Protocol):
    """A training driver that owns the optimizer, loss, and checkpoint loop.

    Concrete impls (e.g. ``PyTorchTrainer`` in
    ``fi_core.training.trainers``) wire a model + dataset + optimizer
    config and run ``fit``. The model and dataset are passed as
    ``Any`` here to keep the Protocol framework-agnostic; the concrete
    trainer narrows the types.
    """

    def fit(
        self,
        *,
        epochs: int,
        save_every: int = 5,
        patience: int = 10,
    ) -> dict[str, Any]:
        """Run the training loop. Returns a metrics summary.

        The summary shape is implementation-defined but must at minimum
        contain ``best_val_loss: float`` and ``global_step: int``.
        """
        ...

    def save_checkpoint(self, path: Path, *, is_best: bool = False) -> None:
        """Persist model + optimizer + scheduler state to ``path``."""
        ...

    def load_checkpoint(self, path: Path) -> None:
        """Restore state previously written by :meth:`save_checkpoint`."""
        ...
