"""What a sync would do to a namespace, and the reasons it must not."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from persona_core.corpus.ingest.documents import CorpusDocument

_IDENTITY = ("sha256", "embed_model", "chunking")


@dataclass(frozen=True)
class StoredDocument:
    document_id: str
    chunks: int
    attributes: dict[str, Any]


@dataclass(frozen=True)
class SyncPlan:
    add: list[CorpusDocument] = field(default_factory=list)
    replace: list[CorpusDocument] = field(default_factory=list)
    delete: list[str] = field(default_factory=list)
    keep: list[str] = field(default_factory=list)
    held: list[str] = field(default_factory=list)
    expected_ids: frozenset[str] = frozenset()
    refusals: list[str] = field(default_factory=list)

    @property
    def writes(self) -> list[CorpusDocument]:
        return [*self.add, *self.replace]

    @property
    def empty(self) -> bool:
        return not (self.add or self.replace or self.delete)


def is_current(document: CorpusDocument, stored: StoredDocument) -> bool:
    """Whether the stored vectors came from these bytes, this policy and this model."""
    return all(stored.attributes.get(k) == document.attributes.get(k) for k in _IDENTITY)


def compute_plan(
    documents: Iterable[CorpusDocument],
    stored: Iterable[StoredDocument],
    *,
    held_ids: Iterable[str] = (),
    max_delete_ratio: float,
    max_deletes: int | None = None,
) -> SyncPlan:
    """The plan for a namespace. `max_deletes` is the operator naming how many deletions they expect.

    Refused: deleting more than `max_delete_ratio` of the namespace without
    naming it, a document left with no chunks, and a held id the store lost.
    """
    wanted = {d.document_id: d for d in documents}
    present = {s.document_id: s for s in stored}
    held = sorted(set(held_ids))
    delete = sorted(set(present) - set(wanted) - set(held))
    both = sorted(set(wanted) & set(present))
    return SyncPlan(
        add=[wanted[i] for i in sorted(set(wanted) - set(present))],
        replace=[wanted[i] for i in both if not is_current(wanted[i], present[i])],
        delete=delete,
        keep=[i for i in both if is_current(wanted[i], present[i])],
        held=held,
        expected_ids=frozenset(present),
        refusals=[
            *(f"{d.document_id}: no text to retrieve in {d.path}" for d in wanted.values() if not d.chunks),
            *(f"{i}: declared held, but the store does not have it" for i in held if i not in present),
            *_delete_refusals(len(delete), len(present), max_delete_ratio, max_deletes),
        ],
    )


def _delete_refusals(deletes: int, present: int, ratio: float, allowed: int | None) -> list[str]:
    limit = int(present * ratio) if allowed is None else allowed
    if deletes <= limit:
        return []
    return [
        f"would delete {deletes} of {present} documents, over the limit of {limit} (--max-deletes {deletes} to mean it)"
    ]


def describe(plan: SyncPlan) -> str:
    """The plan for a human: counts first, then every change that is not an unchanged document."""
    counts = Counter(add=len(plan.add), replace=len(plan.replace), delete=len(plan.delete))
    lines = [
        f"add {counts['add']} · replace {counts['replace']} · delete {counts['delete']} · "
        f"keep {len(plan.keep)} · held {len(plan.held)}"
    ]
    lines += [f"  + {d.document_id} ({len(d.chunks)} chunks)" for d in plan.add]
    lines += [f"  ~ {d.document_id} ({len(d.chunks)} chunks)" for d in plan.replace]
    lines += [f"  - {i}" for i in plan.delete]
    lines += [f"REFUSED: {r}" for r in plan.refusals]
    return "\n".join(lines)
