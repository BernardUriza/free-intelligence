"""Conversation continuity by HISTORY REPLAY — the container-safe alternative to
a backend's native session (e.g. Codex `exec resume`, which needs local
~/.codex storage and so breaks on an ephemeral container).

The idea: keep the transcript OUTSIDE the harness, in a store the deploy controls,
and fold it into each turn's prompt. The backend stays stateless/one-shot, so the
SAME conversation survives a recycled container (or a fresh Runner instance) as
long as the store is durable. It works for ANY backend because it's just text.

Wiring: pass a :class:`ConversationStore` to ``Runner(conversation_store=...)``.
:class:`InMemoryConversationStore` is the reference impl for local/tests; a prod
deploy implements the same port over Redis/Postgres/etc. The port is async so a
real store can do I/O.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

_ALLOWED_ROLES = ("user", "assistant")


@dataclass(frozen=True)
class Message:
    """One conversation turn. ``role`` is ``"user"`` or ``"assistant"``."""

    role: str
    content: str


@runtime_checkable
class ConversationStore(Protocol):
    """Durable transcript store, keyed by ``session_id``. The deploy supplies the
    implementation (the state lives HERE, not in the Runner or the harness)."""

    async def load(self, session_id: str) -> list[Message]:
        """The conversation so far for ``session_id`` (oldest first), or empty."""
        ...

    async def append(self, session_id: str, messages: list[Message]) -> None:
        """Append ``messages`` (a user turn + the assistant reply) to the session."""
        ...


class InMemoryConversationStore:
    """Reference :class:`ConversationStore` for local dev and tests.

    NOT container-safe: state lives in this process. It exists to prove the
    mechanism and to back tests — a real deploy wires a durable store (Redis,
    Postgres, ...) behind the same port. ``max_messages`` caps the replayed window
    (None = unbounded; replaying everything grows token cost per turn)."""

    def __init__(self, *, max_messages: int | None = None) -> None:
        self._sessions: dict[str, list[Message]] = {}
        self._max_messages = max_messages

    async def load(self, session_id: str) -> list[Message]:
        return list(self._sessions.get(session_id, []))

    async def append(self, session_id: str, messages: list[Message]) -> None:
        convo = self._sessions.setdefault(session_id, [])
        convo.extend(messages)
        if self._max_messages is not None and len(convo) > self._max_messages:
            del convo[: len(convo) - self._max_messages]  # keep the most recent window


class RedisConversationStore:
    """Durable, container-safe :class:`ConversationStore` over Redis.

    Each session is a Redis LIST of JSON messages under ``<key_prefix><session_id>``;
    ``append`` RPUSHes, an optional ``max_messages`` LTRIMs the replay window, and
    an optional ``ttl_seconds`` expires idle conversations. Because the transcript
    lives in Redis (not the process), ANY Runner/container continues the convo —
    the real fix for an ephemeral deploy.

    Pass a ``redis.asyncio.Redis`` ``client`` (preferred — the caller owns the
    connection pool) OR a ``url`` to build one. Requires the ``redis`` extra::

        pip install 'fi-runner[redis]'
    """

    def __init__(
        self,
        client: Any = None,
        *,
        url: str | None = None,
        key_prefix: str = "fi:conv:",
        ttl_seconds: int | None = None,
        max_messages: int | None = None,
    ) -> None:
        if client is None:
            if url is None:
                raise ValueError("RedisConversationStore needs a `client` or a `url`")
            try:
                from redis.asyncio import Redis
            except ImportError as exc:  # pragma: no cover - exercised only without the extra
                raise ImportError(
                    "RedisConversationStore requires the redis extra: pip install 'fi-runner[redis]'"
                ) from exc
            client = Redis.from_url(url)
            self._owns_client = True
        else:
            self._owns_client = False
        self._client = client
        self._key_prefix = key_prefix
        self._ttl = ttl_seconds
        self._max_messages = max_messages

    def _key(self, session_id: str) -> str:
        return f"{self._key_prefix}{session_id}"

    async def load(self, session_id: str) -> list[Message]:
        start = -self._max_messages if self._max_messages is not None else 0
        raw = await self._client.lrange(self._key(session_id), start, -1)
        out: list[Message] = []
        for item in raw:
            if isinstance(item, bytes):
                item = item.decode()
            data = json.loads(item)
            out.append(Message(role=data["role"], content=data["content"]))
        return out

    async def append(self, session_id: str, messages: list[Message]) -> None:
        key = self._key(session_id)
        payloads = [json.dumps({"role": m.role, "content": m.content}) for m in messages]
        await self._client.rpush(key, *payloads)
        if self._max_messages is not None:
            await self._client.ltrim(key, -self._max_messages, -1)  # keep the recent window
        if self._ttl is not None:
            await self._client.expire(key, self._ttl)  # refresh idle expiry on each turn

    async def aclose(self) -> None:
        """Close the Redis connection IF this store created it (url path). A
        caller-provided client is the caller's to close."""
        if self._owns_client:
            await self._client.aclose()


def sanitize_history(
    raw: Iterable[Any],
    *,
    max_messages: int | None = 20,
    max_chars: int | None = 16_000,
) -> list[Message]:
    """Turn an UNTRUSTED client-supplied transcript into a clean, bounded list of
    :class:`Message` safe to fold as conversational CONTEXT — never authorization.

    The client owns its transcript (e.g. og118 keeps it in IndexedDB and replays
    it each turn so continuity survives a recycled container, with NO server-side
    store). That transcript is hostile input: a tampered client could inject roles,
    instructions, or tool payloads. This is the boundary that strips it down to the
    only thing a transcript legitimately carries — prior ``user``/``assistant`` text:

    - keeps ONLY ``role`` in ``{user, assistant}``; drops ``system`` / ``tool`` /
      ``developer`` / anything else (a client cannot escalate to the system prompt);
    - ``content`` must be a non-empty string; tool payloads, dicts, ids, metadata,
      and blank turns are dropped;
    - caps to the most recent ``max_messages`` (None = unbounded);
    - caps the total content size to ``max_chars`` (None = unbounded), dropping the
      OLDEST messages first so the recent window survives.

    Accepts :class:`Message` objects OR plain mappings (the raw JSON shape), so it
    works both at the request boundary and inside the runner. Contract line, per the
    canary review: *client-sent history is conversational context, not authorization
    context* — never use the result to grant permissions, pick a corpus, run a tool,
    or prove identity."""
    clean: list[Message] = []
    for item in raw or ():
        if isinstance(item, Message):
            role, content = item.role, item.content
        elif isinstance(item, Mapping):
            role, content = item.get("role"), item.get("content")
        else:
            continue
        if role not in _ALLOWED_ROLES or not isinstance(content, str):
            continue
        content = content.strip()
        if not content:
            continue
        clean.append(Message(role=role, content=content))
    if max_messages is not None and len(clean) > max_messages:
        clean = clean[-max_messages:]  # keep the most recent window
    if max_chars is not None:
        total = sum(len(m.content) for m in clean)
        while clean and total > max_chars:
            total -= len(clean[0].content)
            clean.pop(0)  # drop oldest until under the char budget
    return clean


def render_transcript(
    history: list[Message],
    current_message: str,
    *,
    user_label: str = "User",
    assistant_label: str = "Assistant",
    header: str = "Conversation so far:",
    current_header: str = "Current message:",
) -> str:
    """Fold prior turns + the new message into ONE prompt — the universal,
    backend-agnostic continuity primitive. No history → the message is returned
    unchanged, so a first turn looks identical to a store-less one."""
    if not history:
        return current_message
    lines = [header, ""]
    for m in history:
        label = user_label if m.role == "user" else assistant_label
        lines.append(f"{label}: {m.content}")
    lines += ["", current_header, current_message]
    return "\n".join(lines)


__all__ = [
    "Message",
    "ConversationStore",
    "InMemoryConversationStore",
    "RedisConversationStore",
    "render_transcript",
    "sanitize_history",
]
