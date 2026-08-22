"""Per-turn context bindings for the Runner's ``context_prompt`` hook.

A *context binding* renders the per-turn ``context`` dict into an OPTIONAL
system-prompt addendum, so a consumer can bind structured per-turn state (the
active corpus, a tenant, a locale) into the agent's instructions WITHOUT stuffing
it into the user message — which would pollute the replayed transcript and be
untyped.

Bindings COMPOSE: the Runner holds exactly one ``context_prompt``, so more than
one concern is joined with :func:`compose_bindings` rather than by growing a
single binding that knows about everything.

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
_OWNER_INSTRUCTIONS_PROMPT_PATH = Path(__file__).parent / "prompts" / "owner_instructions_binding.md"

#: Hard cap on owner-authored instruction text reaching the system prompt. The
#: field is free text in a form; without a ceiling a pasted document would push
#: the persona and the guards toward the edge of the window, where models start
#: dropping them. The consumer should reject earlier with a clear error — this is
#: the framework's last line, not the product's validation.
MAX_OWNER_INSTRUCTIONS_CHARS = 4000


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




def owner_instructions_binding(
    *,
    context_key: str = "instructions",
    max_chars: int = MAX_OWNER_INSTRUCTIONS_CHARS,
) -> ContextPrompt:
    """Bind the workspace owner's standing instructions into the system prompt.

    The text is authored by the ACCOUNT OWNER and applies only to that owner's
    own turns, so it is instruction, not untrusted third-party input. The
    template still frames it explicitly — marked as the owner's, fenced by
    markers, and stated to be subordinate to the safety rules and the tool
    policy — because the model otherwise has no way to tell owner text from the
    framework's own words, and a paragraph that opens with "ignore the above"
    would read as if the system had said it.

    Truncated at ``max_chars`` rather than dropped: an owner who pasted too much
    still gets the beginning of what they wrote, and the turn is never silently
    stripped of its instructions.

    Returns ``None`` when the key is absent or blank, so a workspace with no
    instructions produces an addendum byte-identical to having no binding.
    """

    def render(context: Mapping[str, Any]) -> str | None:
        raw = context.get(context_key)
        if not isinstance(raw, str):
            return None
        text = raw.strip()
        if not text:
            return None
        if len(text) > max_chars:
            text = text[:max_chars].rstrip() + "\n[…truncated]"
        return load_prompt(_OWNER_INSTRUCTIONS_PROMPT_PATH).replace("{instructions}", text)

    return render


def compose_bindings(*bindings: ContextPrompt | None) -> ContextPrompt:
    """Join several bindings into the ONE ``context_prompt`` the Runner holds.

    Each is rendered in the order given and the non-empty results are joined by a
    blank line. Order is the caller's and it is meaningful: what comes last sits
    closest to the user message.

    A binding that RAISES is not allowed to take the others down with it — the
    Runner already treats a raising ``context_prompt`` as "no addendum at all",
    which would silently drop a corpus binding because an unrelated one blew up.
    Here the failure is contained to the binding that caused it; the rest of the
    turn keeps its context.
    """
    real = [b for b in bindings if b is not None]

    def render(context: Mapping[str, Any]) -> str | None:
        parts: list[str] = []
        for binding in real:
            try:
                rendered = binding(context)
            except Exception:  # noqa: BLE001 - one bad binding must not blank the others
                continue
            if rendered and rendered.strip():
                parts.append(rendered.strip())
        return "\n\n".join(parts) if parts else None

    return render


__all__ = [
    "MAX_OWNER_INSTRUCTIONS_CHARS",
    "ContextPrompt",
    "active_corpus_binding",
    "compose_bindings",
    "owner_instructions_binding",
]
