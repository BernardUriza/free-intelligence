"""The TOPIC axis — the third axis of the AIRE mapping, driven at its FAILURE modes.

The axis exists because the session was hardcoded to a constant: one Discord
channel, one transcript, forever. Every test here drives the way the fix can be
wrong, not the way it can be right:

- an idle channel that does NOT roll (the axis does nothing),
- an active channel that DOES roll (the conversation is cut in half mid-sentence),
- two messages that fork into two topics (or fold the history twice),
- a redeploy that forks the topic (the whole reason the id is durable),
- Postgres blinking and taking the turn down with it.

The durable store is modelled by ``_TopicsRow``, which implements the claim
statement's semantics in Python — so a "restart" in these tests is exactly what
a restart is in production: the process's RAM is cleared and the row is not.
"""

from __future__ import annotations

import asyncio
import contextlib
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from persona_runner.core.schemas import TurnRequest
from persona_runner.engine import aire_route, aire_topic
from persona_runner.engine.aire_backend import BackendError


class _Clock:
    """A hand-cranked epoch clock — an idle window has to be crossed on purpose,
    never waited for."""

    def __init__(self, now=1_700_000_000.0):
        self.now = now

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class _TopicsRow:
    """The `aire_topics` row, with the claim statement's semantics.

    Deliberately implements the SQL's DECISION (roll when the gap exceeds the
    window, mint from the same clock, clear `answered_at` on a roll) rather than
    stubbing a return value: a stub would pass no matter what the route asked it.
    """

    def __init__(self, clock: _Clock):
        self.clock = clock
        self.rows: dict[str, dict] = {}
        self.created = 0
        self.marks_fail = False

    async def execute(self, sql: str, *args):
        if "CREATE TABLE" in sql:
            self.created += 1
            return
        if sql.strip().startswith("UPDATE"):
            if self.marks_fail:
                raise RuntimeError("pg dropped the mark")
            casita, topic = args
            row = self.rows.get(casita)
            if row is not None and row["topic_id"] == topic:
                row["answered_at"] = self.clock()
            return
        raise AssertionError(f"unexpected statement: {sql}")

    async def fetchrow(self, _sql: str, casita: str, window: float):
        now = self.clock()
        previous = self.rows.get(casita)
        previous_topic = previous["topic_id"] if previous else None
        previous_activity = previous["last_activity_at"] if previous else None
        if previous is None or now - previous["last_activity_at"] > window:
            row = {"topic_id": f"t{int(now)}", "last_activity_at": now, "answered_at": None}
            self.rows[casita] = row
        else:
            row = previous
            row["last_activity_at"] = now
        return {
            "topic_id": row["topic_id"],
            "needs_fold": row["answered_at"] is None,
            "previous_topic_id": previous_topic,
            "previous_activity_at": previous_activity,
        }


@contextlib.asynccontextmanager
async def _acquires(conn):
    yield conn


@pytest.fixture(autouse=True)
def _clean_topic_state():
    """Route caches and the once-per-process DDL flag are module globals."""
    aire_route._backends.clear()
    aire_route._casita_state.clear()
    aire_topic._table_ready = False
    aire_topic._ddl_lock = None
    yield
    aire_route._backends.clear()
    aire_route._casita_state.clear()
    aire_topic._table_ready = False
    aire_topic._ddl_lock = None


@pytest.fixture
def clock():
    return _Clock()


@pytest.fixture
def topics(clock, monkeypatch):
    """A live durable row behind `shared.acquire`, plus the hand-cranked clock."""
    row = _TopicsRow(clock)
    monkeypatch.setattr("persona_runner.mcp_tools.shared.acquire", lambda: _acquires(row))
    monkeypatch.setattr(aire_topic.time, "time", clock)
    return row


class _Result:
    def __init__(self):
        self.text = "hola"
        self.usage = {"input_tokens": 3, "output_tokens": 2}
        self.session_id = "t1"
        self.tool_calls = ()
        self.model = "claude-sonnet-4-6"


class _Door:
    """Records the session AIRE was addressed with, and what was sent to it."""

    def __init__(self):
        self.sessions: list[str] = []
        self.messages: list[str] = []
        self.in_flight = 0
        self.max_in_flight = 0
        self.fail_next = False

    async def run_turn(self, **kwargs):
        self.in_flight += 1
        self.max_in_flight = max(self.max_in_flight, self.in_flight)
        self.sessions.append(kwargs["session_id"])
        self.messages.append(kwargs["user_message"])
        try:
            await asyncio.sleep(0.01)
            if self.fail_next:
                self.fail_next = False
                raise BackendError("AIRE door 500: boom")
            return _Result()
        finally:
            self.in_flight -= 1


@pytest.fixture
def door(monkeypatch):
    d = _Door()
    monkeypatch.setattr(aire_route, "backend_for", lambda _base: d)
    monkeypatch.setattr(aire_route, "fetch_user_facts", AsyncMock(return_value=""))
    monkeypatch.setattr(
        "persona_runner.engine.session_pool._route_model",
        AsyncMock(return_value=("claude-sonnet-4-6", {})),
    )
    return d


def _turn_request(**kw):
    base = {"channel_id": "555", "user_id": "42", "user_text": "hey"}
    base.update(kw)
    return TurnRequest(**base)


def _history():
    return [{"role": "user", "content": "el turno viejo"}]


# --- the rollover rule ------------------------------------------------------


@pytest.mark.asyncio
async def test_a_channel_idle_past_the_window_rolls_to_a_new_topic(topics, clock, monkeypatch):
    """THE POINT OF THE AXIS: without it a Discord channel is one transcript that
    grows for years, every resume loads all of it, and last month's conversation
    rides into today's turn."""
    monkeypatch.setattr(aire_topic.config, "AIRE_TOPIC_IDLE_TIMEOUT_S", 3600.0)
    memory = aire_topic.TopicMemory()

    first = await aire_topic.claim("insult-555", memory)
    clock.advance(3601)
    second = await aire_topic.claim("insult-555", memory)

    assert second.topic_id != first.topic_id
    assert second.rolled_over and second.previous_topic_id == first.topic_id
    assert second.needs_fold, "a fresh AIRE session is empty — the history must ride in"


@pytest.mark.asyncio
async def test_a_channel_inside_the_window_keeps_its_topic(topics, clock, monkeypatch):
    """RESISTANCE: a pause for coffee is not a new conversation. Rolling here
    would cut a live thread in half AND re-pay the persona system prompt."""
    monkeypatch.setattr(aire_topic.config, "AIRE_TOPIC_IDLE_TIMEOUT_S", 3600.0)
    memory = aire_topic.TopicMemory()

    first = await aire_topic.claim("insult-555", memory)
    await aire_topic.mark_answered("insult-555", first.topic_id, memory)
    clock.advance(3599)
    second = await aire_topic.claim("insult-555", memory)

    assert second.topic_id == first.topic_id
    assert not second.rolled_over and not second.opened
    assert not second.needs_fold, "AIRE's session already holds the thread"


@pytest.mark.asyncio
async def test_the_rollover_window_is_the_env_knob_not_a_literal(topics, clock, monkeypatch):
    """The window is tunable per deploy: the same gap rolls or does not roll
    depending only on `AIRE_TOPIC_IDLE_TIMEOUT_S`."""
    memory = aire_topic.TopicMemory()
    monkeypatch.setattr(aire_topic.config, "AIRE_TOPIC_IDLE_TIMEOUT_S", 60.0)
    first = await aire_topic.claim("insult-555", memory)
    clock.advance(120)

    assert (await aire_topic.claim("insult-555", memory)).topic_id != first.topic_id


@pytest.mark.asyncio
async def test_the_first_topic_a_casita_ever_gets_is_an_opening_not_a_rollover(topics):
    """A rollover means context was RESET. Counting a channel's very first topic
    as one would put a reset in the log where nothing was reset."""
    claim = await aire_topic.claim("insult-brand-new", aire_topic.TopicMemory())

    assert claim.opened and not claim.rolled_over and claim.previous_topic_id == ""


@pytest.mark.asyncio
async def test_the_topic_id_is_inside_aires_session_name_allowlist(topics):
    """AIRE validates session names as `[A-Za-z0-9_-]{1,128}` — an id it 422s
    would take down every turn of a rolled-over channel."""
    claim = await aire_topic.claim("insult-555", aire_topic.TopicMemory())

    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-")
    assert set(claim.topic_id) <= allowed and 0 < len(claim.topic_id) <= 128


# --- the casita (the SOUL) must NOT move when the topic does ----------------


@pytest.mark.asyncio
async def test_a_rollover_changes_the_session_and_never_the_casita(topics, clock, door, monkeypatch):
    """The casita is the persona's living identity (`@base` + whatever the
    persona tool wrote). Putting the topic in its NAME would fork that identity
    per topic and re-create the frozen-copies problem thin birth exists to kill."""
    monkeypatch.setattr(aire_topic.config, "AIRE_TOPIC_IDLE_TIMEOUT_S", 3600.0)

    await aire_route.turn_via_aire(_turn_request())
    clock.advance(3601)
    await aire_route.turn_via_aire(_turn_request())

    assert door.sessions[0] != door.sessions[1], "the topic did not roll"
    assert list(aire_route._casita_state) == ["insult-555"], "the casita forked with the topic"
    assert list(topics.rows) == ["insult-555"], "the topic row is keyed by the casita, which never moved"


# --- restart across a redeploy ----------------------------------------------


@pytest.mark.asyncio
async def test_a_process_restart_mid_window_keeps_the_same_topic_id(topics, clock, door, monkeypatch):
    """THE DEFECT A RAM-DERIVED ID WOULD HAVE: this repo redeploys several times a
    day, so an id that lived only in RAM would silently fork the topic
    mid-conversation — same channel, new empty transcript, nobody told."""
    monkeypatch.setattr(aire_topic.config, "AIRE_TOPIC_IDLE_TIMEOUT_S", 3600.0)

    await aire_route.turn_via_aire(_turn_request(history=_history()))
    clock.advance(300)
    aire_route._casita_state.clear()  # ← the redeploy: RAM is gone, the row is not
    await aire_route.turn_via_aire(_turn_request(history=_history()))

    assert door.sessions[0] == door.sessions[1], "a restart forked the topic"


@pytest.mark.asyncio
async def test_a_restart_mid_topic_does_not_re_fold_the_history(topics, clock, door, monkeypatch):
    """The durable `answered_at` is what makes this true, and it is why the fold
    bit moved out of RAM: AIRE's session survives OUR restart, so re-folding
    would duplicate context the session already holds (backlog gap #4)."""
    monkeypatch.setattr(aire_topic.config, "AIRE_TOPIC_IDLE_TIMEOUT_S", 3600.0)

    await aire_route.turn_via_aire(_turn_request(history=_history()))
    clock.advance(300)
    aire_route._casita_state.clear()
    await aire_route.turn_via_aire(_turn_request(history=_history()))

    folded = [m for m in door.messages if "el turno viejo" in m]
    assert len(folded) == 1, f"the history was folded {len(folded)} times into one topic"


# --- concurrency: two messages, one topic, one fold -------------------------


@pytest.mark.asyncio
async def test_two_concurrent_messages_land_in_one_topic_and_fold_history_once(topics, door, monkeypatch):
    """THE RACE: the topic decision sits inside the same per-casita lock as the
    turn, so two messages arriving together cannot mint two topics — nor both
    believe the session is empty and pay for the replayed history twice."""
    monkeypatch.setattr(aire_topic.config, "AIRE_TOPIC_IDLE_TIMEOUT_S", 3600.0)
    req = _turn_request(history=_history())

    await asyncio.gather(aire_route.turn_via_aire(req), aire_route.turn_via_aire(req))

    assert len(set(door.sessions)) == 1, f"two simultaneous messages forked the topic: {door.sessions}"
    assert len([m for m in door.messages if "el turno viejo" in m]) == 1
    assert door.max_in_flight == 1, "the casita gate must serialize same-channel turns"


@pytest.mark.asyncio
async def test_two_channels_get_two_topics_and_are_not_serialized(topics, door, monkeypatch):
    """RESISTANCE: the gate is per casita. Two channels must still run at once,
    each with its own topic and its own fold."""
    monkeypatch.setattr(aire_topic.config, "AIRE_TOPIC_IDLE_TIMEOUT_S", 3600.0)

    await asyncio.gather(
        aire_route.turn_via_aire(_turn_request(channel_id="111", history=_history())),
        aire_route.turn_via_aire(_turn_request(channel_id="222", history=_history())),
    )

    assert door.max_in_flight == 2
    assert len([m for m in door.messages if "el turno viejo" in m]) == 2
    assert len(topics.rows) == 2, "two channels shared one topic row"


# --- failure keeps the fold ------------------------------------------------


@pytest.mark.asyncio
async def test_a_failed_turn_leaves_the_topic_unanswered(topics, door, monkeypatch):
    """RESISTANCE: a turn that never reached AIRE's memory must not consume the
    topic's one history fold — the retry still has to carry the thread."""
    monkeypatch.setattr(aire_topic.config, "AIRE_TOPIC_IDLE_TIMEOUT_S", 3600.0)
    door.fail_next = True
    req = _turn_request(history=_history())

    with pytest.raises(HTTPException):
        await aire_route.turn_via_aire(req)
    await aire_route.turn_via_aire(req)

    assert "el turno viejo" in door.messages[-1]


@pytest.mark.asyncio
async def test_a_lost_mark_write_does_not_buy_a_second_fold(topics, door, monkeypatch):
    """RESISTANCE: the row says "unanswered" only because the mark write was
    dropped, not because the session is empty. This process KNOWS it answered
    there, and that memory may veto a fold — it may never override the topic id."""
    monkeypatch.setattr(aire_topic.config, "AIRE_TOPIC_IDLE_TIMEOUT_S", 3600.0)
    topics.marks_fail = True
    req = _turn_request(history=_history())

    await aire_route.turn_via_aire(req)
    await aire_route.turn_via_aire(req)

    assert len([m for m in door.messages if "el turno viejo" in m]) == 1
    assert len(set(door.sessions)) == 1


# --- Postgres is down -------------------------------------------------------


@pytest.mark.asyncio
async def test_an_unreachable_postgres_still_answers_the_turn(door, monkeypatch):
    """Repo law: a DB fault never kills a turn. The topic degrades to this
    process's memory — same algorithm, smaller lifetime."""
    monkeypatch.setattr("persona_runner.mcp_tools.shared.acquire", lambda: _acquires(None))

    resp = await aire_route.turn_via_aire(_turn_request())

    assert resp.text == "hola" and door.sessions[0].startswith("t")


@pytest.mark.asyncio
async def test_a_raising_database_degrades_to_ram_instead_of_502ing(door, monkeypatch):
    """The same in the uglier direction: the claim statement itself blowing up."""

    class _Boom:
        async def execute(self, *_a):
            raise RuntimeError("pg is down")

        async def fetchrow(self, *_a):
            raise RuntimeError("pg is down")

    monkeypatch.setattr("persona_runner.mcp_tools.shared.acquire", lambda: _acquires(_Boom()))

    claim = await aire_topic.claim("insult-555", aire_topic.TopicMemory())

    assert not claim.durable and claim.topic_id.startswith("t")
    assert (await aire_route.turn_via_aire(_turn_request())).text == "hola"


@pytest.mark.asyncio
async def test_the_ram_fallback_keeps_the_topic_across_a_blip(clock, monkeypatch):
    """A Postgres blip mid-conversation must not roll the topic: the mirror is
    written on every turn precisely so the fallback continues instead of forking."""
    monkeypatch.setattr(aire_topic.config, "AIRE_TOPIC_IDLE_TIMEOUT_S", 3600.0)
    monkeypatch.setattr(aire_topic.time, "time", clock)
    monkeypatch.setattr("persona_runner.mcp_tools.shared.acquire", lambda: _acquires(None))
    memory = aire_topic.TopicMemory()

    first = await aire_topic.claim("insult-555", memory)
    await aire_topic.mark_answered("insult-555", first.topic_id, memory)
    clock.advance(300)
    second = await aire_topic.claim("insult-555", memory)

    assert second.topic_id == first.topic_id and not second.needs_fold


@pytest.mark.asyncio
async def test_the_ram_fallback_is_reported_as_not_durable(monkeypatch):
    """The degradation is a FINDING, not a silence: while it is true a restart
    forks the topic, which is the one thing the durable row exists to prevent."""
    monkeypatch.setattr("persona_runner.mcp_tools.shared.acquire", lambda: _acquires(None))

    assert not (await aire_topic.claim("insult-555", aire_topic.TopicMemory())).durable


# --- the table the runner owns ---------------------------------------------


@pytest.mark.asyncio
async def test_the_topic_table_is_created_once_per_process(topics):
    """The runner owns this table (it is not in the memory store's schema), so it
    creates it on first use — once, not on every turn of every casita."""
    memory = aire_topic.TopicMemory()
    for _ in range(5):
        await aire_topic.claim("insult-555", memory)

    assert topics.created == 1


@pytest.mark.asyncio
async def test_a_failed_create_is_retried_not_cached_as_done(monkeypatch):
    """RESISTANCE: flagging the DDL done after it FAILED would strand the process
    on the RAM path forever, and a restart would then fork every topic."""

    class _DdlBoom:
        async def execute(self, *_a):
            raise RuntimeError("no permission yet")

    monkeypatch.setattr("persona_runner.mcp_tools.shared.acquire", lambda: _acquires(_DdlBoom()))
    await aire_topic.claim("insult-555", aire_topic.TopicMemory())

    assert aire_topic._table_ready is False


# --- the local SDK path is untouched ---------------------------------------


@pytest.mark.asyncio
async def test_the_local_sdk_path_never_touches_the_topic_axis(monkeypatch):
    """The axis is AIRE-only. The local path keeps ONE live SDK session per
    channel — its freshness is `is_open(key)`, and it must not gain a Postgres
    round-trip nor a rollover it has no session semantics for."""
    from persona_runner.api import turn as turn_api

    monkeypatch.setattr(turn_api.config, "TURN_BACKEND", "local")
    monkeypatch.setattr(turn_api, "check_auth", lambda _a: None)
    monkeypatch.setattr(aire_topic, "claim", AsyncMock(side_effect=AssertionError("the local path claimed a topic")))
    monkeypatch.setattr(
        "persona_runner.engine.session_pool.get_or_create_client",
        AsyncMock(side_effect=RuntimeError("local path reached")),
    )

    with pytest.raises(Exception, match="local path reached"):
        await turn_api.turn(_turn_request(), authorization=None)
