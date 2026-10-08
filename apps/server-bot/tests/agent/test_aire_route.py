"""The AIRE route — the guards that must never degrade.

Stage 2 sends every persona turn through AIRE's engine door instead of the local
SDK host. The capability guard, the casita naming and the error mapping are the
three places where a regression would be SILENT, which is exactly the class this
repo crashes the boot over (2026-06-14 / 2026-08-10). Each is asserted here in
both directions: the case that must pass and the case that must NOT.
"""

from __future__ import annotations

import asyncio
import contextlib
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from fi_runner import AIREDoorError
from fi_runner.backend import BackendError

from persona_runner.core.schemas import JudgeRequest, TurnRequest
from persona_runner.engine import aire_route
from persona_runner.engine.aire_route import REQUIRED_BUILTIN_TOOLS


@pytest.fixture(autouse=True)
def _clean_route_state():
    """Each test starts with empty backend caches — they are process-global."""
    aire_route._backends.clear()
    aire_route._judge_backends.clear()
    aire_route._casita_state.clear()
    yield
    aire_route._backends.clear()
    aire_route._judge_backends.clear()
    aire_route._casita_state.clear()


@contextlib.asynccontextmanager
async def _acquires(conn):
    """Stand-in for `mcp_tools.shared.acquire` — hands out one fake connection."""
    yield conn


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
    monkeypatch.setattr(aire_route, "_build_backend", lambda _base: crippled)
    with pytest.raises(RuntimeError, match="required registry tools"):
        aire_route.verify_aire_route()


def test_verify_aire_route_raises_when_the_backend_rides_an_unallowed_mode(_door_env, monkeypatch):
    """Config says `agent` but the wired backend rides something else — caught."""
    monkeypatch.setattr(aire_route.config, "AIRE_TURN_MODE", "agent")
    drifted = aire_route.AIREBackend("insult", default_mode="complete", registry_tools=aire_route.AIRE_REQUIRED_TOOLS)
    monkeypatch.setattr(aire_route, "_build_backend", lambda _base: drifted)
    with pytest.raises(RuntimeError, match="rides mode"):
        aire_route.verify_aire_route()


def test_verifying_the_route_does_not_warm_the_backend_cache(_door_env, monkeypatch):
    """Verification must OBSERVE, never mutate: a boot check that quietly seeds
    the process-wide backend cache is a side effect nothing declares."""
    monkeypatch.setattr(aire_route.config, "AIRE_TURN_MODE", "agent")
    aire_route.verify_aire_route()
    assert aire_route._backends == {}


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


@pytest.mark.parametrize(
    "exc",
    [
        AIREDoorError("AIRE door 422: image 0: fetch answered 404 (expired signature?)", http_status=422),
        AIREDoorError("AIRE door 413: too big", http_status=413),
        AIREDoorError("AIRE turn error [attachment_budget]: session full", code="attachment_budget"),
    ],
)
def test_a_request_the_door_refused_is_terminal_a_retry_would_refetch_and_fail_again(exc):
    """aire-server #50: a 4xx or a full session is never fixed by resending the same request."""
    assert aire_route.to_http_error(exc).status_code == 500


@pytest.mark.parametrize("status", [408, 429])
def test_a_transient_4xx_still_retries(status):
    assert aire_route.to_http_error(AIREDoorError(f"AIRE door {status}", http_status=status)).status_code == 502


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


# --- attachments (every one rides by reference, aire-server #50) ------------

URL = "https://cdn.discordapp.com/attachments/1/2/a.png?ex=ffffffff&is=0&hm=abc"


def test_an_inline_base64_block_is_no_longer_forwarded_it_is_counted_as_dropped():
    """Resistencia (#50): el camino base64 murió; si algo vuelve a mandarlo, se cuenta, no se cuela."""
    images, documents, dropped = aire_route.refs_from_attachments(
        [
            {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": "QUJD"}},
            {"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": "QUJD"}},
        ]
    )
    assert images == [] and documents == [] and dropped == 2


def test_url_blocks_ride_as_references_aire_fetches():
    """The gateway's URL-source blocks become TurnImage(url) and TurnDocument(url, title)."""
    images, documents, dropped = aire_route.refs_from_attachments(
        [
            {"type": "image", "source": {"type": "url", "url": URL}},
            {
                "type": "document",
                "source": {"type": "url", "url": URL.replace("a.png", "acta.pdf")},
                "title": "acta.pdf",
            },
        ]
    )
    assert dropped == 0 and images[0].url == URL and not images[0].data
    assert documents[0].title == "acta.pdf" and documents[0].url.endswith("acta.pdf?ex=ffffffff&is=0&hm=abc")


def test_attachments_lost_maps_to_500_a_retry_resends_the_same_references():
    err = aire_route.to_http_error(
        AIREDoorError("AIRE turn error [attachments_lost]: sent 2, attached 1", code="attachments_lost")
    )
    assert err.status_code == 500


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
        "persona_runner.routing.router_runtime.route_model",
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
        "persona_runner.routing.router_runtime.route_model",
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
        "persona_runner.routing.router_runtime.route_model",
        AsyncMock(return_value=("claude-sonnet-4-6", {})),
    )

    await aire_route.turn_via_aire(_turn_request(behavioral_guidance="cuida a esta persona"))

    sent = backend.run_turn.await_args.kwargs["user_message"]
    assert "toma su tratamiento" in sent
    assert "cuida a esta persona" in sent
    assert "<behavioral_guidance>" in sent


def _bind_recorder(monkeypatch, tmp_path):
    """Wire a turn whose remote memory tools are ON, with a persona dir holding
    insult (the default) and vultur, and record what `aire_principal.bind` gets.
    `turn_via_aire` is where BOTH pipelines meet — the gateway's `caller` turn and
    og118's `runner` turn (api/turn_pipeline's brain calls it) — so this is the
    one place the self-facts owner is decided for every surface."""
    (tmp_path / "insult.md").write_text("# insult")
    (tmp_path / "vultur.md").write_text("# vultur")
    monkeypatch.setattr(aire_route.config, "PERSONAS_DIR", tmp_path)
    monkeypatch.setattr(aire_route.config, "PERSONA_PATH", tmp_path / "insult.md")
    backend = AsyncMock()
    backend.run_turn.return_value = _Result()
    monkeypatch.setattr(aire_route, "backend_for", lambda _base: backend)
    monkeypatch.setattr(aire_route, "fetch_user_facts", AsyncMock(return_value=""))
    monkeypatch.setattr(aire_route, "memory_tool_specs", lambda casita: [f"spec-{casita}"])
    monkeypatch.setattr(
        "persona_runner.routing.router_runtime.route_model",
        AsyncMock(return_value=("claude-sonnet-4-6", {})),
    )
    bound: list[dict] = []

    async def record_bind(casita, **kw):
        bound.append({"casita": casita, **kw})
        return True

    monkeypatch.setattr(aire_route.aire_principal, "bind", record_bind)
    monkeypatch.setattr(aire_route.aire_principal, "clear", AsyncMock())
    return bound


@pytest.mark.asyncio
async def test_the_turn_binds_its_own_persona_as_the_self_facts_owner(monkeypatch, tmp_path):
    """A vultur turn publishes agent_id='vultur' — the persona whose DNA is loaded."""
    bound = _bind_recorder(monkeypatch, tmp_path)

    await aire_route.turn_via_aire(_turn_request(persona_id="vultur"))

    assert bound == [{"casita": "vultur-555", "user_id": "42", "channel_id": "555", "agent_id": "vultur"}]


@pytest.mark.asyncio
@pytest.mark.parametrize("persona_id", ["no_such_persona", "../alice", "alice' OR '1'='1"])
async def test_an_unknown_or_hostile_persona_id_never_becomes_the_self_facts_owner(monkeypatch, tmp_path, persona_id):
    """Resistance: the caller's raw `persona_id` is not trusted as the owner. It
    resolves exactly like the DNA does — to the default persona — so the facts the
    turn may touch always belong to the voice actually speaking, never to a name
    the request smuggled in."""
    bound = _bind_recorder(monkeypatch, tmp_path)

    await aire_route.turn_via_aire(_turn_request(persona_id=persona_id))

    assert [b["agent_id"] for b in bound] == ["insult"]


@pytest.mark.asyncio
async def test_a_cut_turn_raises_instead_of_returning_empty_success(monkeypatch):
    """`budget_exhausted` must surface as an HTTP error, never as a blank reply."""
    backend = AsyncMock()
    backend.run_turn.side_effect = BackendError("AIRE turn error [budget_exhausted]: cut")
    monkeypatch.setattr(aire_route, "backend_for", lambda _base: backend)
    monkeypatch.setattr(aire_route, "fetch_user_facts", AsyncMock(return_value=""))
    monkeypatch.setattr(
        "persona_runner.routing.router_runtime.route_model",
        AsyncMock(return_value=("claude-sonnet-4-6", {})),
    )

    with pytest.raises(HTTPException) as caught:
        await aire_route.turn_via_aire(_turn_request())
    assert caught.value.status_code == 500
    assert aire_route._chat_casita.get() is None  # reset even on the failure path


@pytest.mark.asyncio
async def test_a_budget_cut_is_resent_once_and_the_resend_answers(monkeypatch):
    """AIRE's #23 cut retires the spent client and prescribes its own cure —
    "send the turn again to continue". One resend rides a fresh client on the
    same session; without it the persona answered "…" every time a pooled
    client crossed its ceiling mid-conversation (the 2026-08-26 P1)."""
    backend = AsyncMock()
    backend.run_turn.side_effect = [
        AIREDoorError("AIRE turn error [budget_exhausted]: cut", code="budget_exhausted"),
        _Result(),
    ]
    monkeypatch.setattr(aire_route, "backend_for", lambda _base: backend)
    monkeypatch.setattr(aire_route, "fetch_user_facts", AsyncMock(return_value=""))
    monkeypatch.setattr(
        "persona_runner.routing.router_runtime.route_model",
        AsyncMock(return_value=("claude-sonnet-4-6", {})),
    )

    resp = await aire_route.turn_via_aire(_turn_request())

    assert resp.text == "hola", "the resend AIRE prescribes never happened"
    assert backend.run_turn.await_count == 2


@pytest.mark.asyncio
async def test_a_second_cut_in_a_row_is_terminal_not_a_retry_storm(monkeypatch):
    """The resend is ONE: a client cut twice on the same turn is a real fault
    and maps to 500 exactly as before, so the gateway's neutral path takes over."""
    backend = AsyncMock()
    backend.run_turn.side_effect = AIREDoorError("AIRE turn error [budget_exhausted]: cut", code="budget_exhausted")
    monkeypatch.setattr(aire_route, "backend_for", lambda _base: backend)
    monkeypatch.setattr(aire_route, "fetch_user_facts", AsyncMock(return_value=""))
    monkeypatch.setattr(
        "persona_runner.routing.router_runtime.route_model",
        AsyncMock(return_value=("claude-sonnet-4-6", {})),
    )

    with pytest.raises(HTTPException) as caught:
        await aire_route.turn_via_aire(_turn_request())
    assert caught.value.status_code == 500
    assert backend.run_turn.await_count == 2, "terminal after exactly one resend"


@pytest.mark.asyncio
async def test_other_terminal_codes_are_never_resent(monkeypatch):
    """`budget_exceeded` (the process ceiling) and `credentials_exhausted` are
    not cured by a resend — retrying them is the storm the 500 mapping kills."""
    backend = AsyncMock()
    backend.run_turn.side_effect = AIREDoorError("AIRE turn error [budget_exceeded]: ceiling", code="budget_exceeded")
    monkeypatch.setattr(aire_route, "backend_for", lambda _base: backend)
    monkeypatch.setattr(aire_route, "fetch_user_facts", AsyncMock(return_value=""))
    monkeypatch.setattr(
        "persona_runner.routing.router_runtime.route_model",
        AsyncMock(return_value=("claude-sonnet-4-6", {})),
    )

    with pytest.raises(HTTPException) as caught:
        await aire_route.turn_via_aire(_turn_request())
    assert caught.value.status_code == 500
    assert backend.run_turn.await_count == 1


@pytest.mark.asyncio
async def test_a_credentials_cut_marks_health_and_a_success_clears_it(monkeypatch):
    """/health's `credentials_rejected` must reflect a REAL turn's verdict. With
    the local SDK path gone, the AIRE door's structured code is the only place a
    dead upstream credential is visible — unmarked, the field is a green that
    cannot fail (verify-before-assuming Rule 22)."""
    from persona_runner.engine import auth_failure

    auth_failure.clear_failure()
    failing = AsyncMock()
    exc = BackendError("AIRE turn terminal: credentials pool exhausted")
    exc.code = "credentials_exhausted"
    failing.run_turn.side_effect = exc
    monkeypatch.setattr(aire_route, "backend_for", lambda _base: failing)
    monkeypatch.setattr(aire_route, "fetch_user_facts", AsyncMock(return_value=""))
    monkeypatch.setattr(
        "persona_runner.routing.router_runtime.route_model",
        AsyncMock(return_value=("claude-sonnet-4-6", {})),
    )

    with pytest.raises(HTTPException):
        await aire_route.turn_via_aire(_turn_request())
    recorded = auth_failure.last_failure()
    assert recorded is not None and "credentials" in recorded["detail"]

    healthy = AsyncMock()
    healthy.run_turn.return_value = _Result()
    monkeypatch.setattr(aire_route, "backend_for", lambda _base: healthy)
    await aire_route.turn_via_aire(_turn_request())
    assert auth_failure.last_failure() is None


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

    assert seen and "-judge-" in seen[0]
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
    monkeypatch.setattr("persona_runner.mcp_tools.shared.acquire", lambda: _acquires(conn))

    block = await aire_route.fetch_user_facts("42")

    assert block == "- [health] toma su tratamiento"
    assert not conn.closed, "a POOLED connection is released, never closed"


@pytest.mark.asyncio
async def test_the_hot_path_never_opens_its_own_connection(monkeypatch):
    """The pre-fetch fires on EVERY turn, so it must ride the shared pool — a
    one-shot `_connect` here is a Postgres connect + TLS handshake per turn."""
    conn = _Conn([{"category": "health", "fact": "x"}])
    monkeypatch.setattr("persona_runner.mcp_tools.shared.acquire", lambda: _acquires(conn))
    monkeypatch.setattr(
        "persona_runner.mcp_tools.shared._connect",
        AsyncMock(side_effect=AssertionError("the AIRE fact pre-fetch must not open a one-shot connection")),
    )

    assert await aire_route.fetch_user_facts("42") == "- [health] x"


@pytest.mark.asyncio
async def test_a_dead_database_yields_a_memoryless_turn_not_a_dead_one(monkeypatch):
    """RESISTANCE (repo law): a DB fault never kills the turn."""
    conn = _Conn(boom=True)
    monkeypatch.setattr("persona_runner.mcp_tools.shared.acquire", lambda: _acquires(conn))

    assert await aire_route.fetch_user_facts("42") == ""


@pytest.mark.asyncio
async def test_an_unreachable_postgres_yields_no_facts(monkeypatch):
    """No connection at all is the same contract: empty, never an exception."""
    monkeypatch.setattr("persona_runner.mcp_tools.shared.acquire", lambda: _acquires(None))
    assert await aire_route.fetch_user_facts("42") == ""


@pytest.mark.asyncio
async def test_the_facts_block_is_capped(monkeypatch):
    """An unbounded facts block would push the real message out of the window."""
    conn = _Conn([{"category": "x", "fact": "y" * 50} for _ in range(500)])
    monkeypatch.setattr("persona_runner.mcp_tools.shared.acquire", lambda: _acquires(conn))
    monkeypatch.setattr(aire_route.config, "AIRE_FACTS_MAX_CHARS", 120)

    assert len(await aire_route.fetch_user_facts("42")) == 120


# --- the concurrency invariants (code review 2026-08-22) --------------------
#
# Every test below drives the FAILURE MODE: the interleaving that was possible
# before the fix, at the configuration the fix exists for. A happy-path assert
# here would have passed against the broken code.


class _SlowBackend:
    """A door that takes time, so two turns really overlap. Records what each
    turn SENT and how many were in flight at once."""

    def __init__(self):
        self.messages: list[str] = []
        self.in_flight = 0
        self.max_in_flight = 0
        self.fail_next = False

    async def run_turn(self, **kwargs):
        self.in_flight += 1
        self.max_in_flight = max(self.max_in_flight, self.in_flight)
        self.messages.append(kwargs["user_message"])
        try:
            await asyncio.sleep(0.01)
            if self.fail_next:
                self.fail_next = False
                raise BackendError("AIRE door 500: boom")
            return _Result()
        finally:
            self.in_flight -= 1


def _wire_turn(monkeypatch, backend):
    monkeypatch.setattr(aire_route, "backend_for", lambda _base: backend)
    monkeypatch.setattr(aire_route, "fetch_user_facts", AsyncMock(return_value=""))
    monkeypatch.setattr(
        "persona_runner.routing.router_runtime.route_model",
        AsyncMock(return_value=("claude-sonnet-4-6", {})),
    )


@pytest.mark.asyncio
async def test_two_simultaneous_turns_fold_the_history_exactly_once(monkeypatch):
    """THE RACE: two messages landing together in one channel both used to read
    "not seen" and both folded the whole replayed history — AIRE's per-session
    lock kept it from crashing, so the session just held the conversation twice
    and the tokens were paid twice."""
    backend = _SlowBackend()
    _wire_turn(monkeypatch, backend)
    req = _turn_request(history=[{"role": "user", "content": "el turno viejo"}])

    await asyncio.gather(aire_route.turn_via_aire(req), aire_route.turn_via_aire(req))

    folded = [m for m in backend.messages if "el turno viejo" in m]
    assert len(backend.messages) == 2
    assert len(folded) == 1, f"the history was folded {len(folded)} times into one session"
    assert backend.max_in_flight == 1, "the casita gate must serialize same-channel turns"


@pytest.mark.asyncio
async def test_turns_in_different_channels_are_not_serialized_against_each_other(monkeypatch):
    """RESISTANCE: the gate is per casita, not a process-wide bottleneck — two
    channels must still run concurrently, and each folds its own history."""
    backend = _SlowBackend()
    _wire_turn(monkeypatch, backend)
    history = [{"role": "user", "content": "el turno viejo"}]

    await asyncio.gather(
        aire_route.turn_via_aire(_turn_request(channel_id="111", history=history)),
        aire_route.turn_via_aire(_turn_request(channel_id="222", history=history)),
    )

    assert backend.max_in_flight == 2
    assert len([m for m in backend.messages if "el turno viejo" in m]) == 2


@pytest.mark.asyncio
async def test_a_failed_turn_leaves_the_session_unmarked(monkeypatch):
    """RESISTANCE: a turn that never reached AIRE's memory must not consume the
    one history fold — the retry still has to carry the thread."""
    backend = _SlowBackend()
    backend.fail_next = True
    _wire_turn(monkeypatch, backend)
    req = _turn_request(history=[{"role": "user", "content": "el turno viejo"}])

    with pytest.raises(HTTPException):
        await aire_route.turn_via_aire(req)
    await aire_route.turn_via_aire(req)

    assert "el turno viejo" in backend.messages[-1]


def test_the_casita_state_map_is_bounded(monkeypatch):
    """Each entry carries an asyncio.Lock, so an unbounded map is a real leak on
    a gateway that meets many channels."""
    monkeypatch.setattr(aire_route, "_CASITA_STATE_MAX", 8)

    for n in range(50):
        aire_route.casita_state(f"insult-{n}")

    assert len(aire_route._casita_state) == 8


def test_a_casita_mid_turn_is_never_evicted(monkeypatch):
    """RESISTANCE: dropping a HELD lock would hand the next turn a different lock
    and reopen the race the cap is not allowed to cost."""
    monkeypatch.setattr(aire_route, "_CASITA_STATE_MAX", 2)
    busy = aire_route.casita_state("insult-busy")

    async def _hold_and_flood():
        async with busy.lock:
            for n in range(20):
                aire_route.casita_state(f"insult-{n}")

    asyncio.run(_hold_and_flood())

    assert aire_route._casita_state.get("insult-busy") is busy


# --- the judge's prompt surface (JUDGE_MAX_CONCURRENCY must mean ONE thing) --


class _JudgeDoor:
    """Models AIRE's real hazard: `/init` WRITES the casita's prompt surface and
    the turn reads that surface back after an await. A casita shared by two
    judges is therefore a prompt one can overwrite while the other is mid-turn."""

    def __init__(self):
        self.casita_prompt: dict[str, str] = {}
        self.answered: list[tuple[str, str]] = []
        self._backends: dict[str, _JudgeBackend] = {}

    def backend_for(self, casita: str):
        return self._backends.setdefault(casita, _JudgeBackend(self, casita))


class _JudgeBackend:
    def __init__(self, door: _JudgeDoor, casita: str):
        self.door = door
        self.project = casita
        self.default_mode = "complete"
        self.registry_tools = ()

    async def run_turn(self, **kwargs):
        self.door.casita_prompt[self.project] = kwargs["system_prompt"]
        await asyncio.sleep(0.01)
        self.door.answered.append((kwargs["system_prompt"], self.door.casita_prompt[self.project]))
        return _Result()


@pytest.fixture
def _concurrent_judges(monkeypatch):
    """The configuration the defect hid behind: more than one judge at a time —
    which is SAFE on the local path (a subprocess per judge, each carrying its
    own prompt), so nothing warns you before you raise it."""
    from persona_runner.api import judge as judge_api

    monkeypatch.setattr(judge_api.config, "JUDGE_MAX_CONCURRENCY", 4)
    monkeypatch.setattr(judge_api, "check_auth", lambda _a: None)
    judge_api.reset_judge_semaphore()
    yield judge_api
    judge_api.reset_judge_semaphore()


@pytest.mark.asyncio
async def test_two_concurrent_judges_never_execute_under_each_others_prompt(_concurrent_judges, monkeypatch):
    """THE CROSSING: with one casita per persona, judge B's `/init` lands while
    judge A is mid-turn and A answers under B's instructions — a wrong answer
    that looks perfectly fine. The semaphore hid it only at concurrency 1."""
    judge_api = _concurrent_judges
    door = _JudgeDoor()
    monkeypatch.setattr(aire_route, "judge_backend_for", door.backend_for)

    await asyncio.gather(
        judge_api.judge(JudgeRequest(system_prompt="A: extract facts", user_text="x"), authorization=None),
        judge_api.judge(JudgeRequest(system_prompt="B: reflect on yourself", user_text="y"), authorization=None),
    )

    assert len(door.answered) == 2
    for requested, in_flight in door.answered:
        assert requested == in_flight, "a judge executed under another judge's prompt"
    assert len(door.casita_prompt) == 2, "two differing prompts shared one overwritable casita"


@pytest.mark.asyncio
async def test_many_judges_on_one_identical_prompt_still_share_one_casita(_concurrent_judges, monkeypatch):
    """RESISTANCE: naming the casita after the prompt must not litter the droplet
    — AIRE has a broom for its tables, none for casitas. Identical prompts are
    byte-identical `/init`s, so sharing is safe AND bounded."""
    judge_api = _concurrent_judges
    door = _JudgeDoor()
    monkeypatch.setattr(aire_route, "judge_backend_for", door.backend_for)

    await asyncio.gather(
        *[
            judge_api.judge(JudgeRequest(system_prompt="extract facts", user_text=f"m{n}"), authorization=None)
            for n in range(6)
        ]
    )

    assert len(door.answered) == 6
    assert len(door.casita_prompt) == 1, "one prompt must stay one casita"


def test_the_judge_casita_is_named_after_its_prompt():
    """Same prompt, same casita; a different prompt, a different casita."""
    a = aire_route.judge_casita_for(None, "extract facts")
    again = aire_route.judge_casita_for(None, "extract facts")
    b = aire_route.judge_casita_for(None, "reflect")

    assert a == again and a != b
    assert "-judge-" in a and len(a) <= 128
    assert set(a) <= set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-")


# --- errors classified by CODE, not by prose --------------------------------


def test_a_structured_terminal_code_is_500_even_when_the_prose_changes():
    """AIRE's own error code decides — so a reworded message cannot turn a
    terminal cut into a retry storm."""
    exc = AIREDoorError("la puerta dice otra cosa hoy", code="budget_exhausted")
    assert aire_route.to_http_error(exc).status_code == 500


def test_a_structured_backpressure_code_is_503_even_when_the_prose_changes():
    """The same, in the direction that must stay retryable."""
    exc = AIREDoorError("todas las ranuras ocupadas", code="slot_busy")
    assert aire_route.to_http_error(exc).status_code == 503


def test_an_unknown_structured_code_is_502_not_a_guess():
    """A code AIRE grew that this repo has never classified is upstream-failed,
    not terminal: 502 and retry, never a silent 500."""
    exc = AIREDoorError("AIRE turn error [something_new]: ?", code="something_new")
    assert aire_route.to_http_error(exc).status_code == 502


def test_an_unstructured_reworded_failure_degrades_to_502(monkeypatch):
    """The substring fallback stays for anything unstructured, and its failure
    mode is the SAFE one: a wording change AIRE makes lands on 502-and-retry."""
    exc = BackendError("AIRE turn error: your weekly allowance is spent")
    assert aire_route.to_http_error(exc).status_code == 502


def test_a_door_503_is_backpressure_by_status():
    """An HTTP 503 from the door carries its status as data too."""
    exc = AIREDoorError("AIRE door 503: busy", http_status=503)
    assert aire_route.to_http_error(exc).status_code == 503


# --- shutdown closes what it opened ----------------------------------------


class _Closable:
    def __init__(self, project):
        self.project = project
        self.closed = False

    async def aclose(self):
        self.closed = True


@pytest.mark.asyncio
async def test_close_backends_closes_turn_and_judge_clients():
    """Each AIREBackend holds a pooled httpx.AsyncClient; `aclose()` existed and
    nothing called it, so every one of them leaked past shutdown."""
    turn_b = _Closable("insult")
    judge_b = _Closable("insult-judge-abc")
    aire_route._backends["insult"] = turn_b
    aire_route._judge_backends["insult-judge-abc"] = judge_b

    await aire_route.close_backends()

    assert turn_b.closed and judge_b.closed
    assert aire_route._backends == {} and aire_route._judge_backends == {}


@pytest.mark.asyncio
async def test_one_stubborn_backend_does_not_strand_the_others():
    """RESISTANCE: a client refusing to close must not leave the rest open."""

    class _Stubborn(_Closable):
        async def aclose(self):
            raise RuntimeError("nope")

    aire_route._backends["a"] = _Stubborn("a")
    good = _Closable("b")
    aire_route._judge_backends["b"] = good

    await aire_route.close_backends()

    assert good.closed


@pytest.mark.asyncio
async def test_the_runner_lifespan_closes_the_aire_backends(monkeypatch):
    """The shutdown path itself — the defect was that `_lifespan` closed the
    session pool and nothing else."""
    from persona_runner import runner as runner_mod

    monkeypatch.setattr(aire_route, "verify_aire_route", lambda: None)
    closed_pool = AsyncMock(return_value=None)
    monkeypatch.setattr("persona_runner.mcp_tools.shared.close_pool", closed_pool)
    backend = _Closable("insult")
    aire_route._backends["insult"] = backend

    warm = AsyncMock(return_value=None)
    close_memory = AsyncMock(return_value=None)
    monkeypatch.setattr("persona_runner.api.turn_pipeline.warm_at_boot", warm)
    monkeypatch.setattr("persona_runner.api.turn_pipeline.close_memory", close_memory)

    async with runner_mod._lifespan(object()):
        await asyncio.sleep(0)  # let the boot tasks start

    assert backend.closed, "shutdown left an AIRE door client open"
    closed_pool.assert_awaited_once()
    # Boot warms the pipeline's store + embedder; shutdown releases its pool.
    warm.assert_awaited_once()
    close_memory.assert_awaited_once()


# --- token counts: only what AIRE stated is a number (2026-09-03) -------------


def test_reported_tokens_returns_the_stated_count():
    assert aire_route.reported_tokens({"output_tokens": 1590, "input_tokens": 6}, "output_tokens") == 1590


def test_reported_tokens_keeps_an_explicit_zero():
    """A zero AIRE actually stated is evidence; the gateway may accuse on it."""
    assert aire_route.reported_tokens({"output_tokens": 0}, "output_tokens") == 0


def test_reported_tokens_is_none_when_aire_reported_nothing():
    """THE BUG: `int(usage.get(key, 0) or 0)` turned an absent usage into an
    explicit 0, and the gateway's zero-generation guard degraded Insult's real
    answer to "…" — eight times in two days on AIRE's budget-cut turns."""
    assert aire_route.reported_tokens(None, "output_tokens") is None
    assert aire_route.reported_tokens({}, "output_tokens") is None
    assert aire_route.reported_tokens({"output_tokens": None}, "output_tokens") is None
