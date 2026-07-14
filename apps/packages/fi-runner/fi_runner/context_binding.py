"""Per-turn context bindings for the Runner's ``context_prompt`` hook.

A *context binding* renders the per-turn ``context`` dict into an OPTIONAL
system-prompt addendum, so a consumer can bind structured per-turn state (the
active corpus, a tenant, a locale) into the agent's instructions WITHOUT stuffing
it into the user message — which would pollute the replayed transcript and be
untyped.

``active_corpus_binding`` is the canonical one (the og118 Projects canary): it
binds the turn's ``corpus_id`` AND the search-first policy — with an active
project the agent searches the corpus proactively instead of asking permission.
The addendum's content lives in ``prompts/active_corpus_binding.md`` (prompts are
content, not code) and hot-reloads per turn via ``load_prompt``. The binding is
agnostic to WHAT the corpus id is — the consumer's account model (proj-account)
decides that and passes it in ``context``.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from .prompts import load_prompt

#: A per-turn context → optional system-prompt addendum. Returning ``None`` (or an
#: empty/blank string) means "no addendum this turn" — the runner leaves the
#: persona untouched, byte-identical to a runner without a binding.
ContextPrompt = Callable[[Mapping[str, Any]], "str | None"]

_ACTIVE_CORPUS_PROMPT_PATH = Path(__file__).parent / "prompts" / "active_corpus_binding.md"


def active_corpus_binding(
    *,
    context_key: str = "corpus_id",
    tool_hint: str = "the rag_store tools (search_documents, ingest_document, list_documents, …)",
) -> ContextPrompt:
    """Bind the turn's active corpus + search-first policy into the system prompt.

    Returns a :data:`ContextPrompt` that, when ``context[context_key]`` is set,
    renders ``prompts/active_corpus_binding.md`` with the corpus id: the agent
    must search the active corpus PROACTIVELY (never ask "do you want me to
    search?") and pass that id as ``corpus_id`` to every rag_store tool call.
    Returns ``None`` (no addendum) when the key is absent, so a turn with no
    active project behaves exactly as before.

    ``context_key`` is configurable because the account model decides what the
    value IS; this binding stays agnostic to it.
    """

    def render(context: Mapping[str, Any]) -> str | None:
        corpus = context.get(context_key)
        if not corpus:
            return None
        template = load_prompt(_ACTIVE_CORPUS_PROMPT_PATH)
        return template.replace("{corpus}", str(corpus)).replace("{tool_hint}", tool_hint)

    return render


__all__ = ["ContextPrompt", "active_corpus_binding"]
