"""Per-persona corpus block for the turn path — the seam that revives RAG.

A persona declares `corpus_namespace` in the registry; its injection header is
content at `shared/corpus/headers/<persona_id>.md` (hot-reloaded via the mtime
loader). This module joins the two: given a persona and the user's message, it
retrieves the top corpus chunks and returns a finished, length-capped block for
prompt injection — or None when the persona has no corpus, the query is trivial,
or retrieval finds nothing.

Lives under `shared/` (not `persona_core/`) because it reads the persona
registry and the header content files; it depends on `persona_core.corpus`
for the neutral retrieval, never the reverse. Best-effort: the gateway wraps the
call and any fault here degrades to a turn with no references, never a dead turn.
"""

from __future__ import annotations

from pathlib import Path

import structlog

from persona_core.corpus.references import build_references_block
from persona_core.prompts import PromptCache, load_prompt
from shared.personas.registry import get_persona

log = structlog.get_logger()

_HEADERS_DIR = Path(__file__).resolve().parent / "headers"
_HEADER_CACHE: PromptCache = {}


async def build_persona_corpus_block(*, persona_id: str, query: str | None) -> str | None:
    """Retrieve and format this persona's corpus references for the current turn.

    Returns None when the persona has no `corpus_namespace`, its header file is
    missing, the query is trivial, or nothing clears the similarity floor.
    """
    persona = get_persona(persona_id)
    namespace = getattr(persona, "corpus_namespace", None) if persona else None
    if not namespace:
        return None
    try:
        header = load_prompt(_HEADERS_DIR, persona_id, _HEADER_CACHE)
    except FileNotFoundError:
        log.warning("corpus_header_missing", persona_id=persona_id, namespace=namespace)
        return None
    return await build_references_block(query, namespace=namespace, header=header)
