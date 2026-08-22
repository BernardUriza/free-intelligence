"""Deleting a conversation must delete the session UNDER it.

A consumer's delete removes what the user sees. Before `forget_session`, the
native transcript underneath — the tool_use/tool_result blocks that history
replay structurally cannot carry — survived that delete and became unreachable
forever, because the only id that addressed it had just been thrown away.

Two halves, and the second is the one that is easy to forget: the STORE rows,
and the POOLED CLIENT. A live client still holds the session open and would
write the rows straight back on its next turn, so erasing the store alone
leaves the memory alive behind a name the caller believes is dead.

SDK-free on purpose: `session_key()` is the only thing here that needs the SDK
(it derives the project key from the CLI's cwd), so it is stubbed. What is
under test is the wiring — what gets evicted, what gets deleted, with which key
— not Anthropic's key derivation.
"""

from __future__ import annotations

from typing import Any

import pytest

from fi_runner.backends.claude_code import ClaudeCodeBackend
from fi_runner.runner import Runner


class FakeStore:
    def __init__(self) -> None:
        self.deleted: list[dict[str, str]] = []

    async def delete(self, key: dict[str, str]) -> None:
        self.deleted.append(key)


class FakeClient:
    def __init__(self) -> None:
        self.exited = False

    async def __aexit__(self, *exc: object) -> None:
        self.exited = True


class Backend(ClaudeCodeBackend):
    """The real backend with only the SDK-dependent key derivation stubbed."""

    def session_key(self, session_id: str) -> dict[str, str]:
        return {"project_key": "-test", "session_id": f"uuid5({session_id})"}


def _backend(store: Any = None) -> Backend:
    return Backend(session_store=store)


@pytest.mark.asyncio
async def test_deletes_the_store_rows_under_the_conversation_id() -> None:
    store = FakeStore()
    backend = _backend(store)

    assert await backend.forget_session("conv-1") is True
    assert store.deleted == [{"project_key": "-test", "session_id": "uuid5(conv-1)"}]


@pytest.mark.asyncio
async def test_evicts_the_pooled_client_so_it_cannot_write_the_rows_back() -> None:
    store = FakeStore()
    backend = _backend(store)
    client = FakeClient()
    backend._pool["conv-1"] = client
    backend._session_locks["conv-1"] = __import__("asyncio").Lock()

    await backend.forget_session("conv-1")

    assert client.exited, "the live client was left holding the deleted session open"
    assert "conv-1" not in backend._pool
    assert "conv-1" not in backend._session_locks


@pytest.mark.asyncio
async def test_evicts_even_with_no_store_wired_and_says_it_erased_nothing() -> None:
    backend = _backend(None)
    client = FakeClient()
    backend._pool["conv-1"] = client

    assert await backend.forget_session("conv-1") is False, (
        "no store wired means there was no durable transcript to erase"
    )
    assert client.exited, "the hot cache of a session just declared dead must still go"
    assert "conv-1" not in backend._pool


@pytest.mark.asyncio
async def test_leaves_other_sessions_alone() -> None:
    store = FakeStore()
    backend = _backend(store)
    keep = FakeClient()
    backend._pool["conv-keep"] = keep

    await backend.forget_session("conv-drop")

    assert not keep.exited
    assert backend._pool["conv-keep"] is keep
    assert store.deleted == [{"project_key": "-test", "session_id": "uuid5(conv-drop)"}]


class BackendWithoutNativeMemory:
    """Codex, the fakes — anything that never grew a session store."""


@pytest.mark.asyncio
async def test_runner_is_a_noop_on_a_backend_without_native_memory() -> None:
    runner = Runner(backend=BackendWithoutNativeMemory(), persona="p")  # type: ignore[arg-type]

    assert await runner.forget_session("conv-1") is False, (
        "a consumer's delete must stay byte-identical on a memoryless backend"
    )


@pytest.mark.asyncio
async def test_runner_delegates_to_the_backend() -> None:
    store = FakeStore()
    runner = Runner(backend=_backend(store), persona="p")

    assert await runner.forget_session("conv-1") is True
    assert store.deleted == [{"project_key": "-test", "session_id": "uuid5(conv-1)"}]
