"""Contextual Retrieval — situate each chunk in its document before embedding.

Anthropic's technique: before embedding a chunk, prepend a short LLM-generated
context that places it within the whole document. This cuts top-20 retrieval
failures by ~35% (≈49% paired with contextual BM25, ≈67% with reranking). It's
cheap when the document is prompt-cached (~$1.02 per million doc tokens on Claude)
— exactly the setup fi-core's Claude runners already have.

fi-core stays LLM-agnostic (it BUILDS the prompt, the runner EXECUTES — Shape B):
- :func:`build_contextual_prompt` ships Anthropic's canonical prompt (zero-dep).
- :class:`Contextualizer` is the Protocol the consumer implements with its LLM.
- :class:`CallableContextualizer` adapts a plain ``async (prompt) -> str`` call.

Wire it via ``StoreBackedRetriever(contextualizer=...)``: ingest then embeds the
CONTEXTUALIZED text but stores the ORIGINAL chunk, so citations stay faithful
while recall improves. The consumer should enable prompt caching on the
``<document>`` block so re-contextualizing every chunk of one doc stays cheap.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


def build_contextual_prompt(document: str, chunk: str) -> str:
    """Anthropic's canonical context-generation prompt for one chunk.

    Feed the result to an LLM; the reply is a 1–2 sentence context that situates
    ``chunk`` within ``document`` for retrieval. Keep the ``<document>`` block
    prompt-cached so contextualizing every chunk of a doc reuses it cheaply."""
    return (
        "<document>\n"
        f"{document}\n"
        "</document>\n"
        "Here is the chunk we want to situate within the whole document\n"
        "<chunk>\n"
        f"{chunk}\n"
        "</chunk>\n"
        "Please give a short succinct context to situate this chunk within the overall "
        "document for the purposes of improving search retrieval of the chunk. Answer only "
        "with the succinct context and nothing else."
    )


@runtime_checkable
class Contextualizer(Protocol):
    """Turns ``(document, chunk)`` into a short situating context via an LLM.

    The consumer implements this with whatever model it runs (Claude through the
    fi-runner, Azure OpenAI, ...). fi-core never calls the model itself — see
    :func:`build_contextual_prompt` for the prompt to send."""

    async def contextualize(self, *, document: str, chunk: str) -> str:
        """Return a 1–2 sentence context for ``chunk`` within ``document`` (or
        ``""`` to skip contextualizing this chunk)."""
        ...


@dataclass
class CallableContextualizer:
    """Adapt a plain async LLM call into a :class:`Contextualizer`.

    ``call`` receives the built prompt (:func:`build_contextual_prompt`) and
    returns the model's reply. This is the trivial bridge: wire ``call`` to a
    Claude turn (ideally with the ``<document>`` block prompt-cached)."""

    call: Callable[[str], Awaitable[str]]

    async def contextualize(self, *, document: str, chunk: str) -> str:
        return (await self.call(build_contextual_prompt(document, chunk))).strip()


__all__ = ["Contextualizer", "CallableContextualizer", "build_contextual_prompt"]
