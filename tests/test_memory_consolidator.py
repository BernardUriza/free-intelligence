"""Tests for the Mem0-style memory consolidator (Phase 1, v3.6.0).

Covers:
- JSON judge response parsing (raw + markdown-fenced)
- Plan validation (drops malformed ops; assigns implicit NOOP to omitted ids)
- ADD/UPDATE/DELETE/NOOP application: SQL effects + audit log rows
- Soft-delete invariant: get_facts hides deleted rows; row still exists
- 90-day hard-purge cuts off correctly
- dry_run mode produces a report without touching the DB
- All-users orchestration calls the per-user consolidator once per user
"""

from __future__ import annotations

import json
import tempfile
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from insult.core.memory import MemoryStore
from insult.core.memory_consolidator import (
    SOFT_DELETE_RETENTION_SECONDS,
    _parse_judge_response,
    _validate_plan,
    consolidate_all_users,
    consolidate_user_facts,
    hard_purge_soft_deleted,
)

# ---------------------------------------------------------------------------
# Pure-function tests (no DB, no LLM)
# ---------------------------------------------------------------------------


class TestParseJudgeResponse:
    def test_raw_json_array(self):
        plan = _parse_judge_response('[{"op": "NOOP", "id": 1}]')
        assert plan == [{"op": "NOOP", "id": 1}]

    def test_markdown_fenced(self):
        raw = '```json\n[{"op": "NOOP", "id": 1}]\n```'
        plan = _parse_judge_response(raw)
        assert plan == [{"op": "NOOP", "id": 1}]

    def test_markdown_no_lang(self):
        raw = '```\n[{"op": "DELETE", "id": 5}]\n```'
        assert _parse_judge_response(raw) == [{"op": "DELETE", "id": 5}]

    def test_invalid_json_returns_none(self):
        assert _parse_judge_response("{not valid") is None

    def test_object_instead_of_array_returns_none(self):
        assert _parse_judge_response('{"op": "NOOP"}') is None


class TestValidatePlan:
    def _facts(self, *ids: int) -> list[dict]:
        return [{"id": i, "fact": f"fact-{i}", "category": "general", "updated_at": 0} for i in ids]

    def test_keeps_well_formed_ops(self):
        facts = self._facts(1, 2, 3)
        plan = [
            {"op": "NOOP", "id": 1},
            {"op": "DELETE", "id": 2},
            {"op": "UPDATE", "merge_ids": [3], "new_fact": "merged"},
        ]
        valid = _validate_plan(plan, facts)
        assert len(valid) == 3

    def test_drops_op_with_unknown_id(self):
        plan = [{"op": "DELETE", "id": 999}]
        valid = _validate_plan(plan, self._facts(1, 2))
        # 999 dropped; 1 and 2 omitted by judge → implicit NOOP each
        assert len(valid) == 2
        assert all(op["op"] == "NOOP" for op in valid)

    def test_drops_op_with_duplicate_id(self):
        plan = [{"op": "NOOP", "id": 1}, {"op": "DELETE", "id": 1}]
        valid = _validate_plan(plan, self._facts(1, 2))
        # Second op on id=1 dropped; id=2 → implicit NOOP
        ops_by_kind = [op["op"] for op in valid]
        assert ops_by_kind.count("DELETE") == 0
        assert ops_by_kind.count("NOOP") == 2

    def test_implicit_noop_for_omitted_ids(self):
        # Judge returns plan covering only id=1 — id=2 must get implicit NOOP
        plan = [{"op": "NOOP", "id": 1}]
        valid = _validate_plan(plan, self._facts(1, 2))
        assert {op["id"] for op in valid if op["op"] == "NOOP"} == {1, 2}

    def test_update_merge_ids_filtered_to_known_only(self):
        plan = [{"op": "UPDATE", "merge_ids": [1, 2, 999], "new_fact": "x"}]
        valid = _validate_plan(plan, self._facts(1, 2, 3))
        update = next(op for op in valid if op["op"] == "UPDATE")
        assert update["merge_ids"] == [1, 2]
        # id=3 not consumed → implicit NOOP
        assert any(op["op"] == "NOOP" and op["id"] == 3 for op in valid)


# ---------------------------------------------------------------------------
# DB-touching integration tests with mocked LLM
# ---------------------------------------------------------------------------


@pytest.fixture
async def store():
    """Real SQLite in tempfile so the schema migration runs."""
    with tempfile.TemporaryDirectory() as tmp:
        s = MemoryStore(Path(tmp) / "consolidator_test.db")
        await s.connect()
        try:
            yield s
        finally:
            await s.close()


def _mock_anthropic(judge_plan: list[dict]) -> MagicMock:
    """Build a mock LLMClient whose utility_call returns ``judge_plan`` as JSON.

    Kept the legacy name for test stability; what we mock is now the
    LLMClient wrapper rather than the raw Anthropic client (post-v3.7.62
    consolidator routes through utility_call for cache + retry, with
    JSON output unaffected by the user-facing guards)."""
    from insult.core.llm import LLMResponse

    llm = MagicMock()
    llm.utility_call = AsyncMock(return_value=LLMResponse(text=json.dumps(judge_plan), stop_reason="end_turn"))
    return llm


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

    async def test_delete_op_soft_deletes(self, store):
        await store.add_manual_fact("u1", "live fact 1")
        await store.add_manual_fact("u1", "live fact 2")
        await store.add_manual_fact("u1", "duplicate of fact 1")
        live_before = await store.get_facts("u1")
        assert len(live_before) == 3

        # Judge marks id=3 as duplicate of id=1
        ids = [f["id"] for f in live_before]
        plan = [
            {"op": "NOOP", "id": ids[0], "reason": "standalone"},
            {"op": "NOOP", "id": ids[1], "reason": "standalone"},
            {"op": "DELETE", "id": ids[2], "reason": "duplicate of id=1"},
        ]
        client = _mock_anthropic(plan)
        report = await consolidate_user_facts("u1", memory=store, llm=client, model="claude-haiku-4-5-20251001")

        assert report.counts_by_op()["DELETE"] == 1
        assert report.counts_by_op()["NOOP"] == 2
        live_after = await store.get_facts("u1")
        assert len(live_after) == 2  # soft-deleted hidden from get_facts

        # Row physically still in DB with deleted_at set
        cursor = await store._db.execute("SELECT id, deleted_at FROM user_facts WHERE id = ?", (ids[2],))
        row = await cursor.fetchone()
        assert row is not None
        assert row[1] is not None  # deleted_at populated

    async def test_update_op_creates_merged_fact_and_soft_deletes_originals(self, store):
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

        live_after = await store.get_facts("u1")
        texts = {f["fact"] for f in live_after}
        assert "Vive en Ciudad de México" in texts  # merged
        assert "Vive en CDMX" not in texts  # original soft-deleted
        assert "Está en Ciudad de México" not in texts  # original soft-deleted
        assert "Es programador" in texts  # NOOP preserved
        assert len(live_after) == 2  # 3 in - 2 merged + 1 new = 2


class TestConsolidateUserFactsDryRun:
    async def test_dry_run_does_not_touch_db(self, store):
        await store.add_manual_fact("u1", "f1")
        await store.add_manual_fact("u1", "f2")
        await store.add_manual_fact("u1", "f3")
        live_before = await store.get_facts("u1")
        ids = [f["id"] for f in live_before]

        plan = [{"op": "DELETE", "id": ids[0]}, {"op": "NOOP", "id": ids[1]}, {"op": "NOOP", "id": ids[2]}]
        client = _mock_anthropic(plan)
        report = await consolidate_user_facts(
            "u1", memory=store, llm=client, model="claude-haiku-4-5-20251001", dry_run=True
        )
        assert report.counts_by_op()["DELETE"] == 1
        # DB unchanged
        live_after = await store.get_facts("u1")
        assert len(live_after) == 3
        assert {f["id"] for f in live_after} == {f["id"] for f in live_before}


class TestHardPurge:
    async def test_purges_only_facts_past_retention(self, store):
        await store.add_manual_fact("u1", "old soft-deleted")
        await store.add_manual_fact("u1", "recent soft-deleted")
        await store.add_manual_fact("u1", "still live")
        rows = await store.get_facts("u1")
        old_id = rows[2]["id"]  # oldest insertion = first in display order... use slice 0
        # Manually soft-delete two rows with different timestamps
        old_deleted_at = time.time() - SOFT_DELETE_RETENTION_SECONDS - 86400  # past retention
        recent_deleted_at = time.time() - 3600  # 1h ago, well within retention
        await store._db.execute(
            "UPDATE user_facts SET deleted_at = ? WHERE id = ?",
            (old_deleted_at, rows[0]["id"]),
        )
        await store._db.execute(
            "UPDATE user_facts SET deleted_at = ? WHERE id = ?",
            (recent_deleted_at, rows[1]["id"]),
        )
        await store._db.commit()

        purged = await hard_purge_soft_deleted(store)
        assert purged == 1  # only the old one

        cursor = await store._db.execute("SELECT COUNT(*) FROM user_facts WHERE user_id = 'u1'")
        row = await cursor.fetchone()
        assert row[0] == 2  # 1 still soft-deleted + 1 live remain
        # The "still live" row is unaffected
        live = await store.get_facts("u1")
        assert len(live) == 1
        assert live[0]["id"] == old_id  # still-live row survived


class TestConsolidateAllUsers:
    async def test_iterates_users_with_facts(self, store):
        for u in ("u1", "u2"):
            for i in range(3):
                await store.add_manual_fact(u, f"{u}-fact-{i}")

        # Mock a NOOP-only plan so nothing changes — we only verify orchestration
        client = MagicMock()

        from insult.core.llm import LLMResponse

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
            write_diary=False,
        )
        assert len(reports) == 2
        assert {r.user_id for r in reports} == {"u1", "u2"}
        assert all(r.counts_by_op()["NOOP"] == 3 for r in reports)
        # 2 users x 1 LLM call each (diary disabled in this test)
        assert client.utility_call.await_count == 2
