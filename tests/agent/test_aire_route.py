"""The AIRE route (TURN_BACKEND=aire) — the guards that must never degrade.

Stage 2 sends every persona turn through AIRE's engine door instead of the local
SDK host. The capability guard, the casita naming and the error mapping are the
three places where a regression would be SILENT, which is exactly the class this
repo crashes the boot over (2026-06-14 / 2026-08-10). Each is asserted here in
both directions: the case that must pass and the case that must NOT.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from persona_runner.core.schemas import JudgeRequest, TurnRequest
from persona_runner.engine import aire_route
from persona_runner.engine.aire_backend import BackendError
from persona_runner.engine.options import REQUIRED_BUILTIN_TOOLS


@pytest.fixture(autouse=True)
def _clean_route_state():
    """Each test starts with empty backend caches — they are process-global."""
    aire_route._backends.clear()
    aire_route._judge_backends.clear()
    aire_route._seen_sessions.clear()
    yield
    aire_route._backends.clear()
    aire_route._judge_backends.clear()
    aire_route._seen_sessions.clear()


@pytest.fixture
def _door_env(monkeypatch):
    """A configured door, so env checks pass and no real HTTP is ever attempted."""
    monkeypatch.setenv("AIRE_GATE_URL", "https://gate.example.test")
    monkeypatch.setenv("AIRE_AUTH_TOKEN", "test-token")


# --- the capability guard (the AIRE twin of verify_required_tools) -----------


def test_verify_aire_route_passes_with_a_configured_door(_door_env, monkeypatch):
    """A configured door on an allowlisted mode boots."""
    monkeypatch.setattr(aire_route.config, "AIRE_TURN_MODE", "agent")
    aire_route.verify_aire_route()  # must not raise


def test_verify_aire_route_raises_without_env(monkeypatch):
    """A missing gate URL/token crashes the boot instead of 502ing every turn."""
    monkeypatch.delenv("AIRE_GATE_URL", raising=False)
    monkeypatch.delenv("AIRE_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("AIRE_CANARY_TOKEN", raising=False)
    with pytest.raises(RuntimeError, match="AIRE_GATE_URL"):
        aire_route.verify_aire_route()


def test_verify_aire_route_raises_on_a_mode_without_websearch(_door_env, monkeypatch):
    """`complete` strips WebSearch server-side, so it must never boot a persona."""
    monkeypatch.setattr(aire_route.config, "AIRE_TURN_MODE", "complete")
    with pytest.raises(RuntimeError, match="AIRE_TURN_MODE"):
        aire_route.verify_aire_route()


def test_verify_aire_route_raises_when_a_required_registry_tool_is_dropped(_door_env, monkeypatch):
    """Dropping `persona`/`memory` would cost identity or recall SILENTLY. The
    check asserts the REAL backend a turn would use, so a wiring drift (not just
    a constant edit) is what it catches."""
    monkeypatch.setattr(aire_route.config, "AIRE_TURN_MODE", "agent")
    crippled = aire_route.AIREBackend("insult", default_mode="agent", registry_tools=("persona",))
    monkeypatch.setattr(aire_route, "backend_for", lambda _base: crippled)
    with pytest.raises(RuntimeError, match="required registry tools"):
        aire_route.verify_aire_route()


def test_verify_aire_route_raises_when_the_backend_rides_an_unallowed_mode(_door_env, monkeypatch):
    """Config says `agent` but the wired backend rides something else — caught."""
    monkeypatch.setattr(aire_route.config, "AIRE_TURN_MODE", "agent")
    drifted = aire_route.AIREBackend("insult", default_mode="complete", registry_tools=aire_route.AIRE_REQUIRED_TOOLS)
    monkeypatch.setattr(aire_route, "backend_for", lambda _base: drifted)
    with pytest.raises(RuntimeError, match="rides mode"):
        aire_route.verify_aire_route()


def test_audited_agent_mode_grants_every_required_builtin():
    """The audited server-side surface still carries the load-bearing web tools."""
    allows = aire_route.AUDITED_MODE_ALLOWS["agent"]
    for tool in REQUIRED_BUILTIN_TOOLS:
        assert tool in allows, f"{tool} missing from the audited agent surface: {allows}"


def test_audited_agent_mode_denies_bash():
    """A persona turn must never reach a shell, on either backend."""
    assert "Bash" in aire_route.AUDITED_MODE_DENIES["agent"]


def test_verify_audited_surface_raises_when_the_audit_loses_websearch(monkeypatch):
    """A re-audit that drops WebSearch fails the boot, it does not degrade."""
    monkeypatch.setitem(aire_route.AUDITED_MODE_ALLOWS, "agent", ("Read", "Glob"))
    with pytest.raises(RuntimeError, match="required built-ins"):
        aire_route.verify_audited_surface("agent")


def test_verify_audited_surface_raises_when_the_audit_loses_the_bash_denial(monkeypatch):
    """If AIRE ever stopped denying Bash, this repo refuses to ride that mode."""
    monkeypatch.setitem(aire_route.AUDITED_MODE_DENIES, "agent", ())
    with pytest.raises(RuntimeError, match="does not deny Bash"):
        aire_route.verify_audited_surface("agent")


# --- casita naming (AIRE's allowlist is [A-Za-z0-9_-]{1,128}) ----------------


def test_chat_casita_joins_persona_and_channel():
    """The casita is persona+channel — the decided scoping."""
    assert aire_route.chat_casita_for("insult", "123456") == "insult-123456"


def test_chat_casita_strips_characters_aire_would_404():
    """A channel id carrying anything outside AIRE's allowlist is filtered, not sent."""
    casita = aire_route.chat_casita_for("insult", "12/34?x")
    assert casita == "insult-1234x"


def test_chat_casita_is_capped_at_aires_name_limit():
    """A pathological channel id cannot push the name past AIRE's 128 chars."""
    casita = aire_route.chat_casita_for("insult", "9" * 400)
    assert len(casita) == 128


def test_chat_casita_never_empties_the_channel_half():
    """An id that filters down to nothing still names a distinct casita."""
    assert aire_route.chat_casita_for("insult", "///") == "insult-unknown"


# --- the error contract (a cut turn must never look like success) -----------


def test_budget_exhausted_maps_to_500_so_no_retry_storm_follows():
    """A terminal cut is 500: no retry fixes an exhausted pool."""
    err = aire_route.to_http_error(BackendError("AIRE turn error [budget_exhausted]: cut"))
    assert isinstance(err, HTTPException) and err.status_code == 500


def test_credentials_exhausted_maps_to_500():
    """Every slot dry is terminal too (aire #31)."""
    err = aire_route.to_http_error(BackendError("AIRE turn error [credentials_exhausted]: dry"))
    assert err.status_code == 500


def test_slot_busy_maps_to_503_so_the_transient_retry_applies():
    """Backpressure is NOT terminal — the caller should retry."""
    err = aire_route.to_http_error(BackendError("AIRE turn error [slot_busy]: all 2 slots busy"))
    assert err.status_code == 503


def test_an_unknown_door_failure_maps_to_502():
    """Anything else is a plain upstream failure."""
    err = aire_route.to_http_error(BackendError("AIRE door 500: boom"))
    assert err.status_code == 502


# --- the model-binding finding (measured live 2026-08-22) -------------------


def test_model_diverged_flags_a_different_model():
    """Asking Sonnet and being answered by Haiku is a divergence, not a detail."""
    assert aire_route.model_diverged("claude-sonnet-4-6", "claude-haiku-4-5-20251001")


def test_model_diverged_tolerates_the_dated_build_of_the_same_alias():
    """`claude-sonnet-4-6` answered by `claude-sonnet-4-6-20260514` is honoured."""
    assert not aire_route.model_diverged("claude-sonnet-4-6", "claude-sonnet-4-6-20260514")


def test_model_diverged_is_silent_when_aire_reports_no_model():
    """Absent provenance is not evidence of divergence."""
    assert not aire_route.model_diverged("claude-sonnet-4-6", None)


# --- attachments (AIRE's door takes images only) ----------------------------


def test_image_attachments_are_forwarded_as_aire_blocks():
    """An Anthropic-shape base64 image becomes AIRE's {media_type, data}."""
    images, dropped = aire_route.images_from_attachments(
        [{"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": "QUJD"}}]
    )
    assert dropped == 0
    assert images[0].media_type == "image/png" and images[0].data == "QUJD"


def test_non_image_attachments_are_counted_not_silently_lost():
    """AIRE has no document block — the drop is COUNTED so the caller can log it."""
    images, dropped = aire_route.images_from_attachments(
        [{"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": "QUJD"}}]
    )
    assert images == [] and dropped == 1


# --- the turn itself (backend mocked; no HTTP leaves the test) --------------


class _Result:
    def __init__(self, model="claude-sonnet-4-6"):
        self.text = "hola"
        self.usage = {"input_tokens": 11, "output_tokens": 7}
        self.session_id = "live"
        self.tool_calls = ()
        self.model = model


def _turn_request(**kw):
    base = {"channel_id": "555", "user_id": "42", "user_text": "hey"}
    base.update(kw)
    return TurnRequest(**base)


@pytest.mark.asyncio
async def test_turn_via_aire_addresses_the_persona_channel_casita(monkeypatch):
    """The turn lands in `{persona}-{channel}` and answers with AIRE's provenance."""
    backend = AsyncMock()
    backend.run_turn.return_value = _Result()
    monkeypatch.setattr(aire_route, "backend_for", lambda _base: backend)
    monkeypatch.setattr(aire_route, "fetch_user_facts", AsyncMock(return_value=""))
    monkeypatch.setattr(
        "persona_runner.engine.session_pool._route_model",
        AsyncMock(return_value=("claude-sonnet-4-6", {})),
    )

    resp = await aire_route.turn_via_aire(_turn_request())

    assert resp.text == "hola"
    assert resp.model == "claude-sonnet-4-6"
    assert resp.input_tokens == 11 and resp.output_tokens == 7
    assert aire_route._chat_casita.get() is None  # the ContextVar is always reset


@pytest.mark.asyncio
async def test_turn_via_aire_folds_history_only_on_the_first_turn(monkeypatch):
    """A live AIRE session already holds the thread — re-folding would duplicate it."""
    backend = AsyncMock()
    backend.run_turn.return_value = _Result()
    monkeypatch.setattr(aire_route, "backend_for", lambda _base: backend)
    monkeypatch.setattr(aire_route, "fetch_user_facts", AsyncMock(return_value=""))
    monkeypatch.setattr(
        "persona_runner.engine.session_pool._route_model",
        AsyncMock(return_value=("claude-sonnet-4-6", {})),
    )
    req = _turn_request(history=[{"role": "user", "content": "el turno viejo"}])

    await aire_route.turn_via_aire(req)
    first = backend.run_turn.await_args.kwargs["user_message"]
    await aire_route.turn_via_aire(req)
    second = backend.run_turn.await_args.kwargs["user_message"]

    assert "el turno viejo" in first
    assert "el turno viejo" not in second


@pytest.mark.asyncio
async def test_turn_via_aire_carries_facts_and_guidance_in_band(monkeypatch):
    """Facts + the guardian overlay travel IN the message — no Khimeras credential
    ever reaches the droplet."""
    backend = AsyncMock()
    backend.run_turn.return_value = _Result()
    monkeypatch.setattr(aire_route, "backend_for", lambda _base: backend)
    monkeypatch.setattr(aire_route, "fetch_user_facts", AsyncMock(return_value="- [health] toma su tratamiento"))
    monkeypatch.setattr(
        "persona_runner.engine.session_pool._route_model",
        AsyncMock(return_value=("claude-sonnet-4-6", {})),
    )

    await aire_route.turn_via_aire(_turn_request(behavioral_guidance="cuida a esta persona"))

    sent = backend.run_turn.await_args.kwargs["user_message"]
    assert "toma su tratamiento" in sent
    assert "cuida a esta persona" in sent
    assert "<behavioral_guidance>" in sent


@pytest.mark.asyncio
async def test_a_cut_turn_raises_instead_of_returning_empty_success(monkeypatch):
    """`budget_exhausted` must surface as an HTTP error, never as a blank reply."""
    backend = AsyncMock()
    backend.run_turn.side_effect = BackendError("AIRE turn error [budget_exhausted]: cut")
    monkeypatch.setattr(aire_route, "backend_for", lambda _base: backend)
    monkeypatch.setattr(aire_route, "fetch_user_facts", AsyncMock(return_value=""))
    monkeypatch.setattr(
        "persona_runner.engine.session_pool._route_model",
        AsyncMock(return_value=("claude-sonnet-4-6", {})),
    )

    with pytest.raises(HTTPException) as caught:
        await aire_route.turn_via_aire(_turn_request())
    assert caught.value.status_code == 500
    assert aire_route._chat_casita.get() is None  # reset even on the failure path


@pytest.mark.asyncio
async def test_judge_via_aire_runs_in_the_personas_utility_casita(monkeypatch):
    """The judge is a mode=complete turn in `{persona}-judge`, session-less."""
    backend = AsyncMock()
    backend.run_turn.return_value = _Result(model="claude-haiku-4-5-20251001")
    seen: list[str] = []

    def _capture(casita):
        seen.append(casita)
        return backend

    monkeypatch.setattr(aire_route, "judge_backend_for", _capture)

    resp = await aire_route.judge_via_aire(JudgeRequest(system_prompt="extract facts", user_text="dijo que le duele"))

    assert seen and seen[0].endswith("-judge")
    assert resp.model == "claude-haiku-4-5-20251001"
    assert backend.run_turn.await_args.kwargs["session_id"] is None


def test_judge_backend_rides_complete_mode_with_no_registry_tools():
    """The judge is the raw-API substitute: no builtins, no agentic loop, no tools."""
    backend = aire_route.judge_backend_for("insult-judge")
    assert backend.default_mode == "complete"
    assert backend.registry_tools == ()


# --- the in-band fact pre-fetch (persona_memory cannot run on the droplet) ---


class _Conn:
    def __init__(self, rows=(), boom=False):
        self._rows = list(rows)
        self._boom = boom
        self.closed = False

    async def fetch(self, *_a):
        if self._boom:
            raise RuntimeError("pg is down")
        return self._rows

    async def close(self):
        self.closed = True


@pytest.mark.asyncio
async def test_facts_are_read_in_the_same_line_shape_the_tool_used(monkeypatch):
    """The pre-fetch replaces `get_user_facts`, so the persona must see the same
    `- [category] fact` lines it always saw."""
    conn = _Conn([{"category": "health", "fact": "toma su tratamiento"}])
    monkeypatch.setattr("persona_runner.mcp_tools.shared._connect", AsyncMock(return_value=conn))

    block = await aire_route.fetch_user_facts("42")

    assert block == "- [health] toma su tratamiento"
    assert conn.closed, "the connection must be returned even on the happy path"


@pytest.mark.asyncio
async def test_a_dead_database_yields_a_memoryless_turn_not_a_dead_one(monkeypatch):
    """RESISTANCE (repo law): a DB fault never kills the turn."""
    conn = _Conn(boom=True)
    monkeypatch.setattr("persona_runner.mcp_tools.shared._connect", AsyncMock(return_value=conn))

    assert await aire_route.fetch_user_facts("42") == ""
    assert conn.closed


@pytest.mark.asyncio
async def test_an_unreachable_postgres_yields_no_facts(monkeypatch):
    """No connection at all is the same contract: empty, never an exception."""
    monkeypatch.setattr("persona_runner.mcp_tools.shared._connect", AsyncMock(return_value=None))
    assert await aire_route.fetch_user_facts("42") == ""


@pytest.mark.asyncio
async def test_the_facts_block_is_capped(monkeypatch):
    """An unbounded facts block would push the real message out of the window."""
    conn = _Conn([{"category": "x", "fact": "y" * 50} for _ in range(500)])
    monkeypatch.setattr("persona_runner.mcp_tools.shared._connect", AsyncMock(return_value=conn))
    monkeypatch.setattr(aire_route.config, "AIRE_FACTS_MAX_CHARS", 120)

    assert len(await aire_route.fetch_user_facts("42")) == 120
