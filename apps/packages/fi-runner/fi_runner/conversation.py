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

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


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
    "render_transcript",
]
