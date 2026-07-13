"""The only thing that matters: THE TOOL TRACE SURVIVES A RESTART.

This is what the text history-replay structurally cannot do. `conversation.py`
persists `Message(role, content)` — plain text — and that type cannot represent a
`tool_use` or a `tool_result`. So every tool the agent ran is reported in the
TurnResult and then thrown away: on the next turn it re-reads its own prose but
does NOT remember that it already ran the bash, nor what came back.

The wiring is proven in three assertions, against a REAL Postgres (the memory has
to be durable to mean anything):

    turn 1  → the agent uses a tool; the transcript lands in the store, blocks
              included (tool_use AND its tool_result).
    RESTART → the pool is destroyed. This is the container being recycled: the
              in-RAM client is gone, and before this wiring so was the session.
    turn 2  → the backend asks the STORE (not the pool) whether the session
              exists, and rebuilds the client with `resume=<uuid5>` — never
              `session_id=`, which would silently start a NEW session and stomp
              the transcript it was trying to reach (types.py:1649).

No network, no model, no spend: the SDK client is doubled. What is under test is
the WIRING (which key, which store, what survives) — not Anthropic's inference.
"""

from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
import tempfile
import uuid
from collections.abc import Iterator
from typing import Any

import pytest

asyncpg = pytest.importorskip("asyncpg", reason="the [postgres] extra is not installed")
pytest.importorskip("claude_agent_sdk", reason="the [claude] extra is not installed")

import claude_agent_sdk  # noqa: E402
from claude_agent_sdk import AssistantMessage, ResultMessage, TextBlock, ToolUseBlock  # noqa: E402

from fi_runner.backend import ToolPolicy  # noqa: E402
from fi_runner.backends.claude_code import ClaudeCodeBackend  # noqa: E402
from fi_runner.session_stores import PostgresSessionStore  # noqa: E402


def _pg_bin(name: str) -> str | None:
    for prefix in ("/opt/homebrew/opt/postgresql@17/bin", "/usr/local/opt/postgresql@17/bin"):
        candidate = os.path.join(prefix, name)
        if os.path.exists(candidate):
            return candidate
    return shutil.which(name)


_INITDB, _PG_CTL = _pg_bin("initdb"), _pg_bin("pg_ctl")
pytestmark = pytest.mark.skipif(
    not (_INITDB and _PG_CTL), reason="no local Postgres server binaries for an ephemeral cluster"
)


@pytest.fixture(scope="module")
def ephemeral_postgres() -> Iterator[str]:
    tmp = tempfile.mkdtemp(prefix="fi-runner-pg-")
    data = os.path.join(tmp, "data")
    subprocess.run(
        [_INITDB, "-D", data, "-U", "postgres", "--auth=trust", "-E", "UTF8"],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    # `-l` (log FILE): pg_ctl daemonizes the server, which inherits stdout/stderr.
    # Hand it a pipe and subprocess.run blocks forever waiting for an EOF the
    # daemon never sends.
    subprocess.run(
        [
            _PG_CTL, "-D", data, "-l", os.path.join(tmp, "server.log"), "-o",
            f"-k {tmp} -c listen_addresses='' -c fsync=off -c full_page_writes=off",
            "-w", "start",
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        yield f"postgresql://postgres@/postgres?host={tmp}"
    finally:
        subprocess.run(
            [_PG_CTL, "-D", data, "-m", "immediate", "-w", "stop"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        shutil.rmtree(tmp, ignore_errors=True)


class _FakeSDKClient:
    """Stands in for ClaudeSDKClient. Records the options it was built with, and
    mirrors a transcript into the store the way the SDK does when `session_store`
    is wired — including the blocks plain text cannot carry."""

    built: list[Any] = []

    def __init__(self, options: Any) -> None:
        self.options = options
        _FakeSDKClient.built.append(options)

    async def __aenter__(self) -> "_FakeSDKClient":
        return self

    async def __aexit__(self, *exc: object) -> bool:
        return False

    async def query(self, prompt: Any, **kwargs: Any) -> None:  # noqa: ARG002
        store = getattr(self.options, "session_store", None)
        sid = getattr(self.options, "session_id", None) or getattr(self.options, "resume", None)
        if store is None or sid is None:
            return
        key = {"project_key": "fi-runner", "session_id": sid}
        # What the SDK mirrors: the real transcript, tool blocks and all.
        await store.append(
            key,
            [
                {
                    "uuid": str(uuid.uuid4()),
                    "type": "user",
                    "message": {"role": "user", "content": "¿cuántos archivos hay?"},
                },
                {
                    "uuid": str(uuid.uuid4()),
                    "type": "assistant",
                    "message": {
                        "role": "assistant",
                        "content": [
                            {
                                "type": "tool_use",
                                "id": "toolu_1",
                                "name": "Bash",
                                "input": {"command": "ls | wc -l"},
                            }
                        ],
                    },
                },
                {
                    "uuid": str(uuid.uuid4()),
                    "type": "user",
                    "message": {
                        "role": "user",
                        "content": [
                            {"type": "tool_result", "tool_use_id": "toolu_1", "content": "7"}
                        ],
                    },
                },
            ],
        )

    async def receive_response(self):  # noqa: ANN201
        yield AssistantMessage(
            content=[
                ToolUseBlock(id="toolu_1", name="Bash", input={"command": "ls | wc -l"}),
                TextBlock(text="Hay 7 archivos."),
            ],
            model="claude-sonnet-4-5",
        )
        yield ResultMessage(
            subtype="success",
            duration_ms=1,
            duration_api_ms=1,
            is_error=False,
            num_turns=1,
            session_id="ignored-by-the-backend",
        )


async def _make_store(dsn: str, table: str) -> PostgresSessionStore:
    pool = await asyncpg.create_pool(dsn, min_size=1, max_size=4)
    store = PostgresSessionStore(pool=pool, table=table)
    await store.create_schema()
    return store


def test_the_tool_trace_survives_a_restart(
    ephemeral_postgres: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(claude_agent_sdk, "ClaudeSDKClient", _FakeSDKClient)
    _FakeSDKClient.built.clear()

    async def go() -> None:
        store = await _make_store(ephemeral_postgres, "wiring_survives")
        backend = ClaudeCodeBackend(session_store=store)
        session = "conv-42"  # an arbitrary caller id, NOT a uuid
        sdk_uuid = ClaudeCodeBackend.sdk_session_uuid(session)

        # --- turn 1: the session is BORN. It must be pinned with session_id=.
        await backend.run_turn(
            system_prompt="sé útil",
            user_message="¿cuántos archivos hay?",
            mcp_servers=[],
            tool_policy=ToolPolicy.companion(),
            session_id=session,
        )
        born = _FakeSDKClient.built[-1]
        assert born.session_id == sdk_uuid, "a new session must PIN its id"
        assert born.resume is None, "there is nothing to resume yet"
        assert born.session_store is store
        assert born.session_store_flush == "eager", "a container dies without warning"

        # The trace is in the durable store — the blocks plain text cannot carry.
        entries = await store.load({"project_key": "fi-runner", "session_id": sdk_uuid})
        blocks = [
            b
            for e in entries
            for b in (
                e["message"]["content"] if isinstance(e["message"]["content"], list) else []
            )
        ]
        assert any(b["type"] == "tool_use" and b["name"] == "Bash" for b in blocks), blocks
        assert any(b["type"] == "tool_result" and b["content"] == "7" for b in blocks), blocks

        # --- THE RESTART. The container is recycled: the in-RAM client is gone.
        # Before this wiring, the session died right here.
        backend._pool.clear()
        backend._session_locks.clear()

        # --- turn 2: the backend asks the STORE, finds the session, and RESUMES.
        await backend.run_turn(
            system_prompt="sé útil",
            user_message="¿y qué comando usaste?",
            mcp_servers=[],
            tool_policy=ToolPolicy.companion(),
            session_id=session,
        )
        resumed = _FakeSDKClient.built[-1]
        assert resumed.resume == sdk_uuid, "a known session must be RESUMED from the store"
        assert resumed.session_id is None, (
            "session_id= on a continuation starts a NEW session and stomps the transcript "
            "(types.py:1649) — this is the trap"
        )

        await store._pool.close()

    asyncio.run(go())


def test_without_a_store_nothing_changes(monkeypatch: pytest.MonkeyPatch) -> None:
    """No store wired → byte-identical to before: no session keys on the options,
    no store, and a pool miss is still an amnesiac fresh session. The native path
    is an ADDITION; it does not tax the deploys that do not use it."""
    monkeypatch.setattr(claude_agent_sdk, "ClaudeSDKClient", _FakeSDKClient)
    _FakeSDKClient.built.clear()

    async def go() -> None:
        backend = ClaudeCodeBackend()  # no session_store
        await backend.run_turn(
            system_prompt="sé útil",
            user_message="hola",
            mcp_servers=[],
            tool_policy=ToolPolicy.companion(),
            session_id="conv-42",
        )
        options = _FakeSDKClient.built[-1]
        assert options.session_store is None
        assert options.session_id is None
        assert options.resume is None

    asyncio.run(go())


def test_the_session_uuid_is_deterministic_and_valid() -> None:
    """The SDK demands a UUID (types.py:1649); callers hand us arbitrary strings
    (og118 a conversation id, insult a channel id). uuid5 bridges the two WITHOUT a
    mapping table: the same name always resolves to the same session — which is
    what makes a restart able to find it again."""
    a = ClaudeCodeBackend.sdk_session_uuid("conv-42")
    b = ClaudeCodeBackend.sdk_session_uuid("conv-42")
    c = ClaudeCodeBackend.sdk_session_uuid("conv-43")
    assert a == b, "the same caller id MUST resolve to the same session, forever"
    assert a != c
    assert uuid.UUID(a).version == 5
