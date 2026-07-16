"""Tests for the Mem0-style memory consolidator (Phase 1, v3.6.0).

JSON parsing + plan validation now live in fi-core 0.5.1
(`fi_core.persona.mcp_server.parse_consolidation_result`). The
pure-function tests that previously exercised the local
`_parse_judge_response` / `_validate_plan` were removed when those
functions were deleted in the post-Shape-B cleanup; coverage of that
behavior lives in fi-core's own test suite.

DB-touching tests use the `pg_memory_store` fixture from
`tests/_pg_fixture.py` — they exercise the consolidator end-to-end
against a real PG17 + pgvector so the asyncpg transaction wrapping
in `FactsRepository.apply_consolidation_plan` is verified for real.
"""

from __future__ import annotations

import json
import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from khimeras_shared.consolidation import (
    SOFT_DELETE_RETENTION_SECONDS,
    NoopConsolidationHooks,
    consolidate_all_users,
    consolidate_user_facts,
    hard_purge_soft_deleted,
)
from tests._pg_fixture import REQUIRES_PG

# ---------------------------------------------------------------------------
# DB-touching integration tests with mocked LLM
# ---------------------------------------------------------------------------


# Alias the PG fixture as `store` so the DB-touching tests below keep
# their original parameter names without churning every signature.
@pytest.fixture
async def store(pg_memory_store):
    """Real `MemoryStore` against an ephemeral PG17 with schema applied."""
    return pg_memory_store


def _mock_anthropic(judge_plan: list[dict]) -> MagicMock:
    """Build a mock LLMClient whose utility_call returns ``judge_plan`` as JSON.

    Kept the legacy name for test stability; what we mock is now the
    LLMClient wrapper rather than the raw Anthropic client (post-v3.7.62
    consolidator routes through utility_call for cache + retry, with
    JSON output unaffected by the user-facing guards)."""
    from khimeras_shared.llm import LLMResponse

    llm = MagicMock()
    llm.utility_call = AsyncMock(return_value=LLMResponse(text=json.dumps(judge_plan), stop_reason="end_turn"))
    return llm


@REQUIRES_PG
class TestConsolidateUserFactsApply:
    async def test_skips_when_no_facts(self, store):
        client = _mock_anthropic([])
        report = await consolidate_user_facts("u1", memory=store, llm=client, model="claude-haiku-4-5-20251001")
        assert report.facts_in == 0
        assert report.facts_out == 0
        assert client.utility_call.await_count == 0  # never called LLM

    async def test_skips_when_below_min_facts(self, store):
        await store.add_manual_fact("u1", "fact A")
        await store.add_manual_fact("u1", "fact B")
        client = _mock_anthropic([])
        report = await consolidate_user_facts("u1", memory=store, llm=client, model="claude-haiku-4-5-20251001")
        assert report.facts_in == 2
        # 2 < 3 minimum → no LLM call, no changes
        assert client.utility_call.await_count == 0

    async def test_curated_facts_are_never_deleted(self, store):
        # PROVENANCE GUARD: manual/curated facts (the kind imported + hand-curated
        # for Bernard, and the rescued facts for Alex) are INVISIBLE to the
        # consolidator. Even if the judge returns a DELETE for one, it must not
        # be applied — the fact was never eligible. (2026-06-03 P0 protection.)
        await store.add_manual_fact("u1", "Bernard has CPTSD")
        await store.add_manual_fact("u1", "Bernard takes quetiapina")
        await store.add_manual_fact("u1", "duplicate of fact 1")
        live_before = await store.get_facts("u1")
        assert len(live_before) == 3

        ids = [f["id"] for f in live_before]
        # A malicious/over-eager plan trying to delete a curated fact.
        plan = [
            {"op": "NOOP", "id": ids[0], "reason": "standalone"},
            {"op": "NOOP", "id": ids[1], "reason": "standalone"},
            {"op": "DELETE", "id": ids[2], "reason": "duplicate of id=1"},
        ]
        client = _mock_anthropic(plan)
        await consolidate_user_facts("u1", memory=store, llm=client, model="claude-haiku-4-5-20251001")

        # Nothing deleted — all 3 curated facts still live, untouched.
        live_after = await store.get_facts("u1")
        assert len(live_after) == 3
        assert {f["id"] for f in live_after} == {f["id"] for f in live_before}

    async def test_curated_facts_are_never_merged(self, store):
        # Same guard for UPDATE/merge: curated facts are not folded together.
        await store.add_manual_fact("u1", "Vive en CDMX")
        await store.add_manual_fact("u1", "Está en Ciudad de México")
        await store.add_manual_fact("u1", "Es programador")
        live_before = await store.get_facts("u1")
        ids = sorted([f["id"] for f in live_before])

        plan = [
            {
                "op": "UPDATE",
                "merge_ids": [ids[0], ids[1]],
                "new_fact": "Vive en Ciudad de México",
                "category": "location",
                "reason": "merge duplicate location facts",
            },
            {"op": "NOOP", "id": ids[2]},
        ]
        client = _mock_anthropic(plan)
        await consolidate_user_facts("u1", memory=store, llm=client, model="claude-haiku-4-5-20251001")

        # All three originals survive verbatim — nothing merged away.
        live_after = await store.get_facts("u1")
        texts = {f["fact"] for f in live_after}
        assert "Vive en CDMX" in texts
        assert "Está en Ciudad de México" in texts
        assert "Es programador" in texts
        assert len(live_after) == 3


@REQUIRES_PG
class TestConsolidateUserFactsDryRun:
    async def test_dry_run_does_not_touch_db(self, store):
        await store.add_manual_fact("u1", "f1")
        await store.add_manual_fact("u1", "f2")
        await store.add_manual_fact("u1", "f3")
        live_before = await store.get_facts("u1")
        ids = [f["id"] for f in live_before]

        plan = [{"op": "DELETE", "id": ids[0]}, {"op": "NOOP", "id": ids[1]}, {"op": "NOOP", "id": ids[2]}]
        client = _mock_anthropic(plan)
        await consolidate_user_facts("u1", memory=store, llm=client, model="claude-haiku-4-5-20251001", dry_run=True)
        # DB unchanged — curated facts are guarded, and dry_run never writes anyway.
        live_after = await store.get_facts("u1")
        assert len(live_after) == 3
        assert {f["id"] for f in live_after} == {f["id"] for f in live_before}


@REQUIRES_PG
class TestHardPurge:
    async def test_purges_only_facts_past_retention(self, store):
        await store.add_manual_fact("u1", "old soft-deleted")
        await store.add_manual_fact("u1", "recent soft-deleted")
        await store.add_manual_fact("u1", "still live")
        rows = await store.get_facts("u1")
        old_id = rows[2]["id"]  # oldest insertion = first in display order... use slice 0
        # Manually soft-delete two rows with different timestamps. Goes
        # through the pool directly because the repository API doesn't
        # expose "set deleted_at to an arbitrary historical timestamp" —
        # production only ever soft-deletes at `now`, but the retention
        # test needs to plant rows that look like they aged out.
        old_deleted_at = time.time() - SOFT_DELETE_RETENTION_SECONDS - 86400  # past retention
        recent_deleted_at = time.time() - 3600  # 1h ago, well within retention
        pool = store._manager.pool
        await pool.execute(
            "UPDATE principal_facts SET deleted_at = $1 WHERE id = $2",
            old_deleted_at,
            rows[0]["id"],
        )
        await pool.execute(
            "UPDATE principal_facts SET deleted_at = $1 WHERE id = $2",
            recent_deleted_at,
            rows[1]["id"],
        )

        purged = await hard_purge_soft_deleted(store)
        assert purged == 1  # only the old one

        remaining = await pool.fetchval("SELECT COUNT(*) FROM principal_facts WHERE principal_id = 'u1'")
        assert remaining == 2  # 1 still soft-deleted + 1 live remain
        # The "still live" row is unaffected
        live = await store.get_facts("u1")
        assert len(live) == 1
        assert live[0]["id"] == old_id  # still-live row survived


@REQUIRES_PG
class TestConsolidateAllUsers:
    async def test_iterates_users_with_facts(self, store):
        for u in ("u1", "u2"):
            for i in range(3):
                await store.add_manual_fact(u, f"{u}-fact-{i}")

        # Mock a NOOP-only plan so nothing changes — we only verify orchestration
        client = MagicMock()

        from khimeras_shared.llm import LLMResponse

        def _build_response(system, messages, **kwargs):
            # echo the input fact ids back as NOOPs by inspecting the user prompt
            user_prompt = messages[0]["content"]
            ids = []
            for line in user_prompt.split("\n"):
                if '"id":' in line:
                    chunk = line.split('"id":')[1].split(",")[0].strip()
                    if chunk.isdigit():
                        ids.append(int(chunk))
            plan = [{"op": "NOOP", "id": i} for i in ids]
            return LLMResponse(text=json.dumps(plan), stop_reason="end_turn")

        client.utility_call = AsyncMock(side_effect=_build_response)

        reports = await consolidate_all_users(
            memory=store,
            llm=client,
            model="claude-haiku-4-5-20251001",
            hooks=NoopConsolidationHooks(),
        )
        assert len(reports) == 2
        assert {r.user_id for r in reports} == {"u1", "u2"}
        assert all(r.counts_by_op()["NOOP"] == 3 for r in reports)
        # 2 users x 1 LLM call each (diary disabled in this test)
        assert client.utility_call.await_count == 2
