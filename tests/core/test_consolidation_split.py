"""PR-3d split: the neutral consolidation orchestrator + the hooks contract.

These cover the persona-NEUTRAL half (``khimeras_shared.memory_consolidation``):
the orchestrator calls ``ConsolidationHooks`` at the right boundaries, honors
dry-run, and runs persona-free with ``NoopConsolidationHooks`` (ALICE's path).
The core consolidation behavior (safety-cap, curated guard, apply) stays covered
by ``test_memory_consolidator.py`` through the back-compat shim.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from khimeras_shared import memory_consolidation as mc
from khimeras_shared.memory_consolidation import ConsolidationReport, NoopConsolidationHooks


class SpyHooks:
    """Records every hook call; mimics a real hook by returning None on dry-run
    (so the orchestrator's marker-gated progress is suppressed)."""

    def __init__(self) -> None:
        self.calls: list[tuple] = []

    async def on_run_started(self, *, total_users, dry_run):
        self.calls.append(("started", total_users, dry_run))
        return None if dry_run else "MARKER"

    async def on_user_progress(self, *, marker, total_users, processed_users, current_user_id):
        self.calls.append(("progress", current_user_id))

    async def after_user(self, *, user_id):
        self.calls.append(("after", user_id))

    async def on_pre_finish(self, *, marker, total_users):
        self.calls.append(("pre_finish",))

    async def write_diary(self, reports, *, memory, llm, model, name_resolver):
        self.calls.append(("diary", len(reports)))

    async def on_run_finished(self):
        self.calls.append(("finished",))


def _fake_memory(user_ids):
    mem = MagicMock()
    mem.get_all_facts = AsyncMock(return_value=[{"user_id": u} for u in user_ids])
    return mem


def _stub_core(monkeypatch):
    async def fake_consolidate_user(uid, *, memory, llm, model, dry_run=False):
        return ConsolidationReport(user_id=uid, facts_in=0, facts_out=0)

    monkeypatch.setattr(mc, "consolidate_user_facts", fake_consolidate_user)
    monkeypatch.setattr(mc, "hard_purge_soft_deleted", AsyncMock(return_value=0))


async def test_orchestrator_calls_hooks_in_order(monkeypatch):
    _stub_core(monkeypatch)
    hooks = SpyHooks()
    reports = await mc.consolidate_all_users(memory=_fake_memory(["u1", "u2"]), llm=MagicMock(), model="m", hooks=hooks)
    assert {r.user_id for r in reports} == {"u1", "u2"}
    kinds = [c[0] for c in hooks.calls]
    assert kinds[0] == "started"
    assert kinds.count("progress") == 2  # marker active on real run
    assert kinds.count("after") == 2
    assert "pre_finish" in kinds
    assert ("diary", 2) in hooks.calls
    assert kinds[-1] == "finished"


async def test_orchestrator_dry_run_skips_side_effects(monkeypatch):
    _stub_core(monkeypatch)
    purge = AsyncMock(return_value=0)
    monkeypatch.setattr(mc, "hard_purge_soft_deleted", purge)
    hooks = SpyHooks()
    await mc.consolidate_all_users(memory=_fake_memory(["u1"]), llm=MagicMock(), model="m", hooks=hooks, dry_run=True)
    kinds = [c[0] for c in hooks.calls]
    # dry-run: marker is None → no progress; after/pre_finish/diary/finished all gated off.
    assert kinds == ["started"]
    purge.assert_not_awaited()


async def test_noop_hooks_run_persona_free(monkeypatch):
    _stub_core(monkeypatch)
    reports = await mc.consolidate_all_users(
        memory=_fake_memory(["u1"]), llm=MagicMock(), model="m", hooks=NoopConsolidationHooks()
    )
    assert len(reports) == 1


def test_insult_hooks_conform_to_contract():
    from personas.insult.core.consolidation_hooks import InsultConsolidationHooks

    h = InsultConsolidationHooks()
    for method in (
        "on_run_started",
        "on_user_progress",
        "after_user",
        "on_pre_finish",
        "write_diary",
        "on_run_finished",
    ):
        assert callable(getattr(h, method)), method


async def test_shim_consolidate_all_users_wires_insult_hooks(monkeypatch):
    """The back-compat shim must delegate to the neutral orchestrator with
    Insult's hooks, preserving the old (no-hooks) signature."""
    from personas.insult.core import memory_consolidator as shim

    captured = {}

    async def fake_neutral(*, memory, llm, model, hooks, dry_run=False, name_resolver=None):
        captured["hooks_type"] = type(hooks).__name__
        captured["dry_run"] = dry_run
        return []

    monkeypatch.setattr(shim, "_consolidate_all_users_neutral", fake_neutral)

    await shim.consolidate_all_users(memory=MagicMock(), llm=MagicMock(), model="m", write_diary=False)
    assert captured["hooks_type"] == "InsultConsolidationHooks"
