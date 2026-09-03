"""The credential failover (#31), engine-side and offline: the rotor's ordering
and cooldown, the lying-green detection predicate, and the rotate-and-retry
flow over a faked drain — no real API calls, no real CLI subprocesses."""

import asyncio
from types import SimpleNamespace

from aire.engine import credentials
from aire.engine.contract import TurnResult, TurnSpec
from aire.engine.core import Engine
from aire.engine.credentials import Rotor, limit_hit
from aire.engine.options import build_options

LIMIT_TEXT = "You've hit your weekly limit · resets Aug 10, 8pm (UTC)"
ZERO_USAGE = {"input_tokens": 0, "output_tokens": 0, "total_cost_usd": 0}
FULL_ENV = {"CLAUDE_CODE_OAUTH_TOKEN": "tok-a",
            "CLAUDE_CODE_OAUTH_TOKEN_BACKUP": "tok-b",
            "ANTHROPIC_API_KEY_FALLBACK": "key-c"}


def test_rotor_orders_the_chain_and_skips_empty_slots():
    rotor = Rotor({"CLAUDE_CODE_OAUTH_TOKEN": "tok-a",
                   "CLAUDE_CODE_OAUTH_TOKEN_BACKUP": "",
                   "ANTHROPIC_API_KEY_FALLBACK": "key-c"})
    assert [s.name for s in rotor.slots] == ["oauth-primary", "api-key-fallback"]
    assert rotor.slots[0].env == {"CLAUDE_CODE_OAUTH_TOKEN": "tok-a", "ANTHROPIC_API_KEY": ""}
    assert rotor.slots[1].env == {"ANTHROPIC_API_KEY": "key-c", "CLAUDE_CODE_OAUTH_TOKEN": ""}


def test_rotor_with_no_slots_is_one_ambient_slot_injecting_nothing():
    rotor = Rotor({})
    assert [s.name for s in rotor.slots] == ["ambient"]
    assert rotor.active().env == {}


def test_burn_rotates_and_all_dry_returns_none():
    rotor = Rotor(FULL_ENV)
    assert rotor.active().name == "oauth-primary"
    rotor.burn("oauth-primary")
    assert rotor.active().name == "oauth-backup"
    rotor.burn("oauth-backup")
    rotor.burn("api-key-fallback")
    assert rotor.active() is None
    assert rotor.cooling_names() == ["api-key-fallback", "oauth-backup", "oauth-primary"]
    assert 0 < rotor.retry_after_s() <= credentials.COOLDOWN_S


def test_cooldown_expiry_requalifies_the_slot(monkeypatch):
    clock = [1000.0]
    monkeypatch.setattr(credentials, "time", SimpleNamespace(monotonic=lambda: clock[0]))
    rotor = Rotor({"CLAUDE_CODE_OAUTH_TOKEN": "tok-a"})
    rotor.burn("oauth-primary")
    assert rotor.active() is None
    clock[0] += credentials.COOLDOWN_S + 1
    assert rotor.active().name == "oauth-primary"
    assert rotor.cooling_names() == []


def test_limit_hit_needs_both_the_phrase_and_zero_usage():
    assert limit_hit(LIMIT_TEXT, ZERO_USAGE)
    assert limit_hit(LIMIT_TEXT, None)
    assert limit_hit("Usage limit reached · resets tomorrow", ZERO_USAGE)
    assert limit_hit("You've hit your session limit · resets 11:20pm (UTC)", ZERO_USAGE), \
        "the 5-hour window's notice (measured live 2026-09-03) must turn the rotor too"
    assert not limit_hit(LIMIT_TEXT, {**ZERO_USAGE, "output_tokens": 42})
    assert not limit_hit("Here is your poem about limits", ZERO_USAGE)
    assert not limit_hit("", ZERO_USAGE)
    assert not limit_hit(None, ZERO_USAGE)


def _engine_with(rotor: Rotor, results: list[TurnResult]) -> tuple[Engine, dict]:
    engine = Engine(session_store=object())
    engine.rotor = rotor
    seen = {"drains": 0, "retired": 0, "slots_used": []}

    async def fake_client_for(project, session, spec, slot=None):
        engine.slot_of[f"{project}/{session}"] = slot.name
        seen["slots_used"].append(slot.name)
        return SimpleNamespace(query=_noop), asyncio.Lock()

    async def fake_retire(project, session):
        seen["retired"] += 1
        engine.slot_of.pop(f"{project}/{session}", None)

    async def fake_drain(client):
        result = results[min(seen["drains"], len(results) - 1)]
        seen["drains"] += 1
        yield {"type": "result", "result": result}

    engine._client_for = fake_client_for
    engine._retire = fake_retire
    import aire.engine.turn as turn
    turn_drain = turn.drain
    turn.drain = fake_drain
    seen["restore"] = lambda: setattr(turn, "drain", turn_drain)
    return engine, seen


async def _collect(engine: Engine) -> list[dict]:
    return [ev async for ev in engine.run_stream("proj", "sess", "hi", TurnSpec(mode="complete"))]


def test_limit_hit_rotates_retries_once_and_yields_only_the_real_result():
    lying = TurnResult(text=LIMIT_TEXT, usage=ZERO_USAGE)
    good = TurnResult(text="OK", usage={"output_tokens": 3, "total_cost_usd": 0.01})
    engine, seen = _engine_with(Rotor(FULL_ENV), [lying, good])
    try:
        events = asyncio.run(_collect(engine))
    finally:
        seen["restore"]()
    assert [e["type"] for e in events] == ["result"]
    assert events[0]["result"].text == "OK"
    assert seen["drains"] == 2
    assert seen["retired"] == 1
    assert seen["slots_used"] == ["oauth-primary", "oauth-backup"]
    assert engine.rotor.cooling_names() == ["oauth-primary"]


def test_all_slots_dry_emits_a_real_error_one_attempt_per_slot():
    lying = TurnResult(text=LIMIT_TEXT, usage=ZERO_USAGE)
    engine, seen = _engine_with(Rotor(FULL_ENV), [lying])
    try:
        events = asyncio.run(_collect(engine))
    finally:
        seen["restore"]()
    assert seen["drains"] == 3
    assert [e.get("error") for e in events] == ["credentials_exhausted"]
    assert events[0]["cooling"] == ["api-key-fallback", "oauth-backup", "oauth-primary"]
    assert "next probe in" in events[0]["detail"]


def test_slot_env_composes_with_the_gateway_scrub(tmp_path):
    rotor = Rotor({"CLAUDE_CODE_OAUTH_TOKEN_BACKUP": "tok-b"})
    options = build_options(object(), "proj", str(tmp_path), "u" * 8,
                            TurnSpec(mode="complete"),
                            resuming=False, credential_env=rotor.active().env)
    assert options.env["ANTHROPIC_BASE_URL"] == "https://api.anthropic.com"
    assert options.env["ANTHROPIC_AUTH_TOKEN"] == ""
    assert options.env["CLAUDE_CODE_OAUTH_TOKEN"] == "tok-b"
    assert options.env["ANTHROPIC_API_KEY"] == ""


def test_spec_model_reaches_the_sdk_and_absence_leaves_the_engine_deciding(tmp_path):
    asked = build_options(object(), "proj", str(tmp_path), "u" * 8,
                          TurnSpec(mode="complete", model="claude-haiku-4-5"), resuming=False)
    silent = build_options(object(), "proj", str(tmp_path), "u" * 8,
                           TurnSpec(mode="complete"), resuming=False)
    assert asked.model == "claude-haiku-4-5"
    assert silent.model is None


def test_the_client_cap_is_born_only_on_a_metered_slot(tmp_path, monkeypatch):
    monkeypatch.setenv("AIRE_MAX_BUDGET_USD", "1.0")
    spec = TurnSpec(mode="complete")
    card = build_options(object(), "proj", str(tmp_path), "u" * 8, spec, resuming=False,
                         metered=True)
    subscription = build_options(object(), "proj", str(tmp_path), "u" * 8, spec,
                                 resuming=False, metered=False)
    unknown = build_options(object(), "proj", str(tmp_path), "u" * 8, spec, resuming=False)
    assert card.max_budget_usd == 1.0
    assert subscription.max_budget_usd is None, "nominal dollars must not cut the client"
    assert unknown.max_budget_usd == 1.0, "an unknown slot counts as real money"


async def _noop(*args, **kwargs):
    return None
