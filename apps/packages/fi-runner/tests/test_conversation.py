"""Tests for history-replay continuity — the container-safe alternative to a
backend's native session.

The point: state lives in the ConversationStore, NOT the Runner or the harness.
A fresh Runner with the same store continues the conversation; a stateless
backend never gets a session_id; guards see the ORIGINAL message, not the folded
transcript; a crash stores no half turn.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field

import pytest

from fi_runner import (
    BackendError,
    InMemoryConversationStore,
    Message,
    RedisConversationStore,
    Runner,
    TurnResult,
    render_transcript,
    triage_guard,
)


@dataclass
class _SpyBackend:
    """Records the user_message + session_id the runner handed it."""

    reply: str = "ok"
    seen_user: list[str] = field(default_factory=list)
    seen_session: list[str | None] = field(default_factory=list)

    async def run_turn(self, *, user_message, session_id=None, **_kw) -> TurnResult:  # noqa: ANN001, ANN003
        self.seen_user.append(user_message)
        self.seen_session.append(session_id)
        return TurnResult(text=self.reply)


@dataclass
class _BoomBackend:
    async def run_turn(self, **_kw) -> TurnResult:  # noqa: ANN003
        raise RuntimeError("model down")


class _FakeRedis:
    """Minimal async Redis fake — emulates LIST semantics for the store tests."""

    def __init__(self) -> None:
        self.lists: dict[str, list[str]] = {}
        self.ttls: dict[str, int] = {}

    async def rpush(self, key, *values) -> int:  # noqa: ANN001
        self.lists.setdefault(key, []).extend(values)
        return len(self.lists[key])

    async def lrange(self, key, start, stop) -> list:  # noqa: ANN001
        lst = self.lists.get(key, [])
        return lst[start : (None if stop == -1 else stop + 1)]  # redis stop is inclusive

    async def ltrim(self, key, start, stop) -> bool:  # noqa: ANN001
        lst = self.lists.get(key, [])
        self.lists[key] = lst[start : (None if stop == -1 else stop + 1)]
        return True

    async def expire(self, key, seconds) -> bool:  # noqa: ANN001
        self.ttls[key] = seconds
        return True


def _event_sink() -> tuple[list[tuple[str, dict]], Callable[[str, dict], None]]:
    events: list[tuple[str, dict]] = []
    return events, lambda e, f: events.append((e, f))


def _runner(backend, store=None, **kw) -> Runner:  # noqa: ANN001
    return Runner(backend=backend, persona="p", conversation_store=store, flow_narrator=None, **kw)


# --- render_transcript (pure) -------------------------------------------------


def test_render_transcript_empty_returns_message_unchanged():
    assert render_transcript([], "hola") == "hola"


def test_render_transcript_folds_prior_turns():
    history = [Message("user", "¿hora?"), Message("assistant", "las 3")]
    out = render_transcript(history, "¿y ahora?")
    assert "User: ¿hora?" in out and "Assistant: las 3" in out
    assert out.rstrip().endswith("¿y ahora?")  # current message last


# --- InMemoryConversationStore ------------------------------------------------


@pytest.mark.asyncio
async def test_in_memory_store_load_append_roundtrip():
    store = InMemoryConversationStore()
    assert await store.load("c1") == []
    await store.append("c1", [Message("user", "a"), Message("assistant", "b")])
    assert [m.content for m in await store.load("c1")] == ["a", "b"]


@pytest.mark.asyncio
async def test_in_memory_store_window_caps_history():
    store = InMemoryConversationStore(max_messages=2)
    await store.append("c1", [Message("user", "a"), Message("assistant", "b")])
    await store.append("c1", [Message("user", "c"), Message("assistant", "d")])
    assert [m.content for m in await store.load("c1")] == ["c", "d"]  # oldest dropped


# --- runner integration -------------------------------------------------------


@pytest.mark.asyncio
async def test_second_turn_replays_first_into_the_prompt():
    store = InMemoryConversationStore()
    backend = _SpyBackend(reply="r1")
    runner = _runner(backend, store)
    await runner.run("hola", session_id="c1")
    assert backend.seen_user[0] == "hola"  # turn 1: no history → raw message

    backend.reply = "r2"
    await runner.run("¿y antes?", session_id="c1")
    folded = backend.seen_user[1]
    assert "hola" in folded and "r1" in folded and "¿y antes?" in folded  # turn 1 replayed
    # backend stays stateless: it never receives a session_id under replay
    assert backend.seen_session == [None, None]
    # the store holds the ORIGINAL user messages + replies
    assert [m.content for m in await store.load("c1")] == ["hola", "r1", "¿y antes?", "r2"]


@pytest.mark.asyncio
async def test_continuity_survives_a_fresh_runner_instance():
    # THE point: state lives in the store, not the Runner. A brand-new Runner
    # (as if a recycled container spun up a new process) continues the convo.
    store = InMemoryConversationStore()
    await _runner(_SpyBackend(reply="a1"), store).run("uno", session_id="c1")

    b2 = _SpyBackend(reply="a2")
    await _runner(b2, store).run("dos", session_id="c1")  # different Runner + backend
    assert "uno" in b2.seen_user[0] and "a1" in b2.seen_user[0]


@pytest.mark.asyncio
async def test_without_store_session_id_passes_through_to_backend():
    backend = _SpyBackend()
    await _runner(backend).run("hola", session_id="c1")  # no store
    assert backend.seen_user[0] == "hola"  # not folded
    assert backend.seen_session[0] == "c1"  # backend-native session used instead


@pytest.mark.asyncio
async def test_history_replayed_event_only_when_history_exists():
    events, sink = _event_sink()
    store = InMemoryConversationStore()
    runner = _runner(_SpyBackend(), store, on_event=sink)
    await runner.run("a", session_id="c1")
    assert not [e for e, _ in events if e == "history_replayed"]  # first turn: nothing to replay
    await runner.run("b", session_id="c1")
    replayed = [f for e, f in events if e == "history_replayed"]
    assert len(replayed) == 1 and replayed[0]["messages"] == 2 and replayed[0]["session_id"] == "c1"


@pytest.mark.asyncio
async def test_crash_stores_no_half_turn():
    store = InMemoryConversationStore()
    runner = _runner(_BoomBackend(), store)
    with pytest.raises(BackendError):
        await runner.run("hola", session_id="c1")
    assert await store.load("c1") == []  # nothing persisted on failure


@pytest.mark.asyncio
async def test_guards_see_original_message_not_the_folded_transcript():
    # A prior crisis in the transcript must NOT re-trigger triage on a later calm
    # turn — guards get the ORIGINAL user_message, the backend gets the fold.
    store = InMemoryConversationStore()
    events, sink = _event_sink()
    runner = _runner(_SpyBackend(reply="estable"), store, guards=[triage_guard("psychiatry")], on_event=sink)
    await runner.run("el paciente refiere plan suicida", session_id="c1")  # turn 1: critical
    events.clear()
    await runner.run("hoy se siente estable", session_id="c1")  # turn 2: calm ORIGINAL
    levels = [f for e, f in events if e == "turn_completed"][0]["guard_levels"]
    assert levels["triage"] != "CRITICAL"  # the folded prior crisis did NOT leak into guards


# --- RedisConversationStore (durable; fake client, no real redis) -------------


@pytest.mark.asyncio
async def test_redis_store_roundtrip():
    store = RedisConversationStore(client=_FakeRedis(), key_prefix="t:")
    assert await store.load("c1") == []
    await store.append("c1", [Message("user", "a"), Message("assistant", "b")])
    assert [(m.role, m.content) for m in await store.load("c1")] == [("user", "a"), ("assistant", "b")]


@pytest.mark.asyncio
async def test_redis_store_applies_window_and_ttl():
    fake = _FakeRedis()
    store = RedisConversationStore(client=fake, key_prefix="t:", max_messages=2, ttl_seconds=3600)
    await store.append("c1", [Message("user", "a"), Message("assistant", "b")])
    await store.append("c1", [Message("user", "c"), Message("assistant", "d")])
    assert [m.content for m in await store.load("c1")] == ["c", "d"]  # LTRIM kept the window
    assert fake.ttls["t:c1"] == 3600  # EXPIRE refreshed each append


@pytest.mark.asyncio
async def test_redis_store_decodes_bytes_payloads():
    fake = _FakeRedis()
    fake.lists["t:c1"] = [json.dumps({"role": "user", "content": "hola"}).encode()]  # decode_responses=False
    store = RedisConversationStore(client=fake, key_prefix="t:")
    assert (await store.load("c1"))[0].content == "hola"


def test_redis_store_requires_client_or_url():
    with pytest.raises(ValueError, match="client"):
        RedisConversationStore()


@pytest.mark.asyncio
async def test_redis_store_drives_runner_continuity_across_instances():
    # The durable store satisfies the port: a fresh Runner continues the convo.
    store = RedisConversationStore(client=_FakeRedis())
    await _runner(_SpyBackend(reply="r1"), store).run("hola", session_id="c1")
    b2 = _SpyBackend(reply="r2")
    await _runner(b2, store).run("otra", session_id="c1")  # different Runner instance
    assert "hola" in b2.seen_user[0] and "r1" in b2.seen_user[0]
