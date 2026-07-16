"""Mem0-style user-fact consolidation — the neutral capability, modularized.

Package layout (one module per responsibility):

- ``clinical_guard``: the code layer that refuses destructive ops on clinical
  facts, whatever the judge asked (the cluster that protects Alex).
- ``judge``: the single Haiku call over the full fact snapshot, Shape B via
  fi-core's builder/parser, with OUR conservative system prompt.
- ``contracts``: audit-op/report dataclasses and the ``ConsolidationHooks``
  protocol personas implement.
- ``orchestrator``: the safety-cap and provenance policy, the per-user pass,
  the all-users run, and the soft-delete hard purge.

Replaces the former ``khimeras_shared.memory_consolidation`` monolith
(deleted 2026-07-16); this package is its only home.
"""

from khimeras_shared.consolidation.clinical_guard import (
    CLINICAL_CATEGORIES,
    filter_clinical_destruction,
    is_clinical_fact,
)
from khimeras_shared.consolidation.contracts import (
    ConsolidationHooks,
    ConsolidationReport,
    FactOperation,
    NoopConsolidationHooks,
)
from khimeras_shared.consolidation.judge import JUDGE_MAX_OUTPUT_TOKENS
from khimeras_shared.consolidation.orchestrator import (
    CONSOLIDATION_MAX_DESTROY_FRACTION,
    CONSOLIDATION_MIN_DESTROY_TO_CAP,
    CURATED_SOURCES,
    SOFT_DELETE_RETENTION_SECONDS,
    consolidate_all_users,
    consolidate_user_facts,
    hard_purge_soft_deleted,
)

__all__ = [
    "CLINICAL_CATEGORIES",
    "CONSOLIDATION_MAX_DESTROY_FRACTION",
    "CONSOLIDATION_MIN_DESTROY_TO_CAP",
    "CURATED_SOURCES",
    "JUDGE_MAX_OUTPUT_TOKENS",
    "SOFT_DELETE_RETENTION_SECONDS",
    "ConsolidationHooks",
    "ConsolidationReport",
    "FactOperation",
    "NoopConsolidationHooks",
    "consolidate_all_users",
    "consolidate_user_facts",
    "filter_clinical_destruction",
    "hard_purge_soft_deleted",
    "is_clinical_fact",
]
