"""Back-compat shim — the consolidator split into capability + persona hooks (PR-3d).

The neutral consolidation core + orchestrator moved to
``khimeras_shared.memory_consolidation``; Insult's persona side effects (siesta
sleep coordination + dream diary + deep_memory ingest) live in
``personas.insult.core.consolidation_hooks.InsultConsolidationHooks``.

This module preserves the historical Insult-facing surface so existing callers
(``composition.py`` re-exports, ``__main__`` admin CLI, ``siesta/diary`` typing,
the test suite) are untouched. ``consolidate_all_users`` keeps its old signature
and wires Insult's hooks into the neutral orchestrator.
"""

from __future__ import annotations

from khimeras_shared.memory_consolidation import (
    CONSOLIDATION_MAX_DESTROY_FRACTION as CONSOLIDATION_MAX_DESTROY_FRACTION,
)
from khimeras_shared.memory_consolidation import (
    CONSOLIDATION_MIN_DESTROY_TO_CAP as CONSOLIDATION_MIN_DESTROY_TO_CAP,
)
from khimeras_shared.memory_consolidation import (
    CURATED_SOURCES as CURATED_SOURCES,
)
from khimeras_shared.memory_consolidation import (
    JUDGE_MAX_OUTPUT_TOKENS as JUDGE_MAX_OUTPUT_TOKENS,
)
from khimeras_shared.memory_consolidation import (
    SOFT_DELETE_RETENTION_SECONDS as SOFT_DELETE_RETENTION_SECONDS,
)
from khimeras_shared.memory_consolidation import (
    ConsolidationReport as ConsolidationReport,
)
from khimeras_shared.memory_consolidation import (
    FactOperation as FactOperation,
)
from khimeras_shared.memory_consolidation import (
    consolidate_all_users as _consolidate_all_users_neutral,
)
from khimeras_shared.memory_consolidation import (
    consolidate_user_facts as consolidate_user_facts,
)
from khimeras_shared.memory_consolidation import (
    hard_purge_soft_deleted as hard_purge_soft_deleted,
)


async def consolidate_all_users(
    *,
    memory,
    llm,
    model: str,
    dry_run: bool = False,
    write_diary: bool = True,
    name_resolver: dict[str, str] | None = None,
) -> list[ConsolidationReport]:
    """Run consolidation across every user with facts, wiring Insult's hooks.

    Back-compat surface: same signature as before the PR-3d split. The
    ``write_diary`` flag is carried by Insult's hooks (which no-op the diary when
    it's False); siesta + deep_memory ingest run through those hooks too.
    """
    from personas.insult.core.consolidation_hooks import InsultConsolidationHooks

    return await _consolidate_all_users_neutral(
        memory=memory,
        llm=llm,
        model=model,
        hooks=InsultConsolidationHooks(write_diary=write_diary),
        dry_run=dry_run,
        name_resolver=name_resolver,
    )
