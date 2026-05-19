"""Tests for `fi_core.memory.consolidator.FactConsolidator`.

Uses an in-memory mock MemoryStore to verify orchestration end-to-end
without spinning up Postgres. The persona.mcp_server tools are real
(deterministic regex + JSON parsing) so the integration is genuine.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

from fi_core.memory import Fact, FactSource, MemoryStore
from fi_core.memory.consolidator import (
    DEFAULT_MIN_FACTS,
    FactConsolidator,
)
from fi_core.memory.types import ConsolidationOp


# ---------------------------------------------------------------------------
# Mock store — satisfies MemoryStore Protocol with in-memory dicts.
# ---------------------------------------------------------------------------


class _MockStore:
    """Minimal MemoryStore for unit tests.

    Stores facts as a list keyed by principal_id. Applies plans in-memory
    so the consolidator orchestration can be tested without Postgres.
    """

    def __init__(self) -> None:
        self._facts: dict[str, list[Fact]] = {}
        self._next_id: int = 1
        self.applied_plans: list[tuple[str, list[dict[str, Any]]]] = []

    def seed(self, principal_id: str, facts: list[str]) -> list[int]:
        ids: list[int] = []
        for text in facts:
            fid = self._next_id
            self._next_id += 1
            self._facts.setdefault(principal_id, []).append(
                Fact(
                    id=fid,
                    fact=text,
                    principal_id=principal_id,
                    updated_at=1000.0,
                )
            )
            ids.append(fid)
        return ids

    async def get_facts(
        self, principal_id: str, *, include_deleted: bool = False
    ) -> list[Fact]:
        return [
            f
            for f in self._facts.get(principal_id, [])
            if include_deleted or f.deleted_at is None
        ]

    async def save_facts(self, principal_id: str, facts: list[Fact]) -> None:
        # Replace AUTO facts only — mirror PgMemoryStore semantics
        self._facts[principal_id] = [
            f
            for f in self._facts.get(principal_id, [])
            if f.source != FactSource.AUTO
        ]
        for f in facts:
            fid = self._next_id
            self._next_id += 1
            self._facts.setdefault(principal_id, []).append(
                Fact(
                    id=fid,
                    fact=f.fact,
                    principal_id=principal_id,
                    category=f.category,
                    source=FactSource.AUTO,
                    updated_at=f.updated_at,
                )
            )

    async def add_fact(
        self,
        principal_id: str,
        fact: str,
        *,
        category: str = "general",
        source: FactSource | None = None,
    ) -> int:
        fid = self._next_id
        self._next_id += 1
        self._facts.setdefault(principal_id, []).append(
            Fact(
                id=fid,
                fact=fact,
                principal_id=principal_id,
                category=category,
                source=source or FactSource.MANUAL,
            )
        )
        return fid

    async def soft_delete_fact(self, fact_id: int, *, deleted_at: float) -> bool:
        for pid_facts in self._facts.values():
            for i, f in enumerate(pid_facts):
                if f.id == fact_id and f.deleted_at is None:
                    pid_facts[i] = Fact(
                        id=f.id,
                        fact=f.fact,
                        principal_id=f.principal_id,
                        category=f.category,
                        source=f.source,
                        updated_at=f.updated_at,
                        deleted_at=deleted_at,
                    )
                    return True
        return False

    async def purge_soft_deleted(self, cutoff: float) -> int:
        removed = 0
        for pid, facts in self._facts.items():
            keep: list[Fact] = []
            for f in facts:
                if f.deleted_at is not None and f.deleted_at < cutoff:
                    removed += 1
                else:
                    keep.append(f)
            self._facts[pid] = keep
        return removed

    async def count_live(self, principal_id: str) -> int:
        return len(
            [f for f in self._facts.get(principal_id, []) if f.deleted_at is None]
        )

    async def semantic_search(
        self, principal_id: str, query: str, *, limit: int = 10
    ) -> list[Fact]:  # noqa: ARG002
        return (await self.get_facts(principal_id))[:limit]

    async def apply_consolidation_plan(
        self,
        principal_id: str,
        plan: list[dict[str, Any]],
        *,
        run_ts: float,
    ) -> list[ConsolidationOp]:
        self.applied_plans.append((principal_id, plan))
        applied: list[ConsolidationOp] = []
        live = await self.get_facts(principal_id)
        by_id = {f.id: f for f in live if f.id is not None}

        for op in plan:
            kind = op["op"]
            reason = op.get("reason", "")
            if kind == "NOOP":
                fid = op["id"]
                applied.append(
                    ConsolidationOp(
                        op="NOOP",
                        fact_id_before=fid,
                        fact_id_after=fid,
                        fact_text_before=by_id[fid].fact if fid in by_id else None,
                        fact_text_after=by_id[fid].fact if fid in by_id else None,
                        reason=reason,
                        run_ts=run_ts,
                    )
                )
            elif kind == "DELETE":
                fid = op["id"]
                await self.soft_delete_fact(fid, deleted_at=run_ts)
                applied.append(
                    ConsolidationOp(
                        op="DELETE",
                        fact_id_before=fid,
                        fact_id_after=None,
                        fact_text_before=by_id[fid].fact if fid in by_id else None,
                        fact_text_after=None,
                        reason=reason,
                        run_ts=run_ts,
                    )
                )
            elif kind == "UPDATE":
                merge_ids = op["merge_ids"]
                new_text = op["new_fact"]
                for fid in merge_ids:
                    await self.soft_delete_fact(fid, deleted_at=run_ts)
                new_id = await self.add_fact(
                    principal_id, new_text, source=FactSource.AUTO
                )
                for fid in merge_ids:
                    applied.append(
                        ConsolidationOp(
                            op="UPDATE",
                            fact_id_before=fid,
                            fact_id_after=new_id,
                            fact_text_before=by_id[fid].fact if fid in by_id else None,
                            fact_text_after=new_text,
                            reason=reason,
                            run_ts=run_ts,
                        )
                    )
        return applied

    async def init_schema(self) -> None:
        pass

    async def close(self) -> None:
        pass


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestProtocolSatisfaction:
    def test_mock_store_satisfies_protocol(self):
        assert isinstance(_MockStore(), MemoryStore)


class TestConsolidatorSkipsLowFactCount:
    async def test_below_min_facts_short_circuits(self):
        store = _MockStore()
        store.seed("u1", ["one fact only"])  # 1 < DEFAULT_MIN_FACTS (3)

        async def _judge(system, user, max_tokens):  # noqa: ARG001
            pytest.fail("LLM should NOT be called below min_facts")

        consolidator = FactConsolidator(store=store, llm_call=_judge)
        report = await consolidator.consolidate_principal("u1")

        assert report.facts_in == 1
        assert report.facts_out == 1
        assert report.error is None
        assert report.ops == []


class TestConsolidatorAppliesPlan:
    async def test_judge_returns_valid_noop_plan(self):
        store = _MockStore()
        ids = store.seed("u1", ["fact A", "fact B", "fact C"])

        async def _judge(system, user, max_tokens):  # noqa: ARG001
            # Return a plan that NOOPs all three
            return json.dumps([{"op": "NOOP", "id": i} for i in ids])

        consolidator = FactConsolidator(store=store, llm_call=_judge)
        report = await consolidator.consolidate_principal("u1")

        assert report.facts_in == 3
        assert report.facts_out == 3
        assert len(report.ops) == 3
        assert all(op.op == "NOOP" for op in report.ops)
        assert report.error is None

    async def test_judge_returns_delete_plan_reduces_facts(self):
        store = _MockStore()
        ids = store.seed("u1", ["keep me", "delete me", "merge me 1", "merge me 2"])

        async def _judge(system, user, max_tokens):  # noqa: ARG001
            return json.dumps(
                [
                    {"op": "NOOP", "id": ids[0]},
                    {"op": "DELETE", "id": ids[1], "reason": "obsolete"},
                    {
                        "op": "UPDATE",
                        "merge_ids": [ids[2], ids[3]],
                        "new_fact": "merged",
                        "reason": "redundant",
                    },
                ]
            )

        consolidator = FactConsolidator(store=store, llm_call=_judge)
        report = await consolidator.consolidate_principal("u1")

        assert report.facts_in == 4
        # 1 NOOP + 1 UPDATE result = 2 live facts post-apply
        assert report.facts_out == 2

    async def test_dry_run_does_not_mutate_store(self):
        store = _MockStore()
        ids = store.seed("u1", ["a", "b", "c"])

        async def _judge(system, user, max_tokens):  # noqa: ARG001
            return json.dumps([{"op": "DELETE", "id": i} for i in ids])

        consolidator = FactConsolidator(store=store, llm_call=_judge)
        report = await consolidator.consolidate_principal("u1", dry_run=True)

        # Plan synthesized but NOT applied
        assert len(report.ops) == 3
        assert store.applied_plans == []
        # Store unchanged
        live = await store.get_facts("u1")
        assert len(live) == 3


class TestConsolidatorErrorHandling:
    async def test_llm_failure_captured_in_report(self):
        store = _MockStore()
        store.seed("u1", ["a", "b", "c"])

        async def _judge(system, user, max_tokens):  # noqa: ARG001
            raise RuntimeError("API timeout")

        consolidator = FactConsolidator(store=store, llm_call=_judge)
        report = await consolidator.consolidate_principal("u1")

        assert report.error is not None
        assert "llm_call_failed" in report.error
        assert report.ops == []

    async def test_unparseable_response_captured(self):
        store = _MockStore()
        store.seed("u1", ["a", "b", "c"])

        async def _judge(system, user, max_tokens):  # noqa: ARG001
            return "this is not JSON"

        consolidator = FactConsolidator(store=store, llm_call=_judge)
        report = await consolidator.consolidate_principal("u1")

        assert report.error is not None
        assert "parse_failed" in report.error


class TestConsolidatorThresholdConfig:
    async def test_custom_min_facts_threshold(self):
        store = _MockStore()
        store.seed("u1", ["only one"])  # 1 fact

        async def _judge(system, user, max_tokens):  # noqa: ARG001
            return json.dumps([{"op": "NOOP", "id": 1}])

        consolidator = FactConsolidator(
            store=store, llm_call=_judge, min_facts=1
        )
        report = await consolidator.consolidate_principal("u1")

        assert report.error is None
        assert len(report.ops) == 1


def test_default_min_facts_constant():
    assert DEFAULT_MIN_FACTS == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
