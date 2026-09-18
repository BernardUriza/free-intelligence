"""The ACP backend — one adapter for every agent that speaks the Agent Client
Protocol (JSON-RPC over stdio: Claude Code, Codex, Gemini, Qwen, Kimi, Mistral,
Grok, MiniMax, GLM, opencode, goose, …). The engine sees an `AgentClient`; the
protocol sees a client that spawns the agent, opens or loads a session, prompts,
and reads updates until the stop reason.

What ACP does NOT give, and this backend does not pretend: a system prompt
(the agent reads its own context files from the casita `cwd`), a pluggable
session store (AIRE mirrors every update itself — `acp_mirror`), and the model
that answered (only the agent's name). A session loaded on a WARM box resumes
the agent's memory; on a cold box the agent has nothing to load and a fresh
session is opened LOUDLY (`ACP-RESUME-LOST`) — the mirror holds the transcript,
the agent does not, and re-priming it is #49's next step, not a silent fork."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

import acp
from acp import schema
from acp.client.connection import ClientSideConnection

from .. import acp_mirror
from .acp_bridge import Bridge
from .acp_messages import collect_blocks, result_message
from .acp_roster import AcpAgent, roster
from .base import Birth


@dataclass(frozen=True)
class AcpOptions:
    agent: AcpAgent
    cwd: str
    project_key: str
    session_uuid: str
    allow_tools: bool
    env: dict[str, str] = field(default_factory=dict)


def build_options(birth: Birth) -> AcpOptions:
    from .claude import project_key_for_directory
    agent = roster()[birth.spec.provider]
    return AcpOptions(agent=agent, cwd=birth.cwd,
                      project_key=project_key_for_directory(birth.cwd),
                      session_uuid=birth.session_uuid,
                      allow_tools=birth.spec.mode == "agent",
                      env={**agent.env, **(birth.credential_env or {})})


def client(options: AcpOptions) -> "AcpClient":
    return AcpClient(options)


class AcpClient:
    def __init__(self, options: AcpOptions) -> None:
        self.o = options
        self.bridge = Bridge(options.agent.name, options.allow_tools, self._mirror)
        self.session_id = ""
        self._task: asyncio.Task[Any] | None = None
        self._conn: ClientSideConnection | None = None
        self._spawn: Any = None
        self._can_load = False

    async def _mirror(self, kind: str, entry: dict[str, Any]) -> None:
        await acp_mirror.append(self.o.project_key, self.o.session_uuid,
                                self.o.agent.name, self.session_id or None, kind, entry)

    async def __aenter__(self) -> "AcpClient":
        self._spawn = acp.spawn_agent_process(self.bridge, *self.o.agent.command,
                                              env=self.o.env or None, cwd=self.o.cwd)
        self._conn, _ = await self._spawn.__aenter__()
        init = await self._conn.initialize(protocol_version=acp.PROTOCOL_VERSION,
                                           client_capabilities=schema.ClientCapabilities())
        caps = init.agent_capabilities
        self._can_load = bool(caps and caps.load_session)
        await self._open_session()
        return self

    async def _open_session(self) -> None:
        assert self._conn is not None
        known = await acp_mirror.agent_session(self.o.project_key, self.o.session_uuid,
                                               self.o.agent.name)
        if known and self._can_load:
            try:
                await self._conn.load_session(cwd=self.o.cwd, session_id=known, mcp_servers=[])
                self.session_id = known
                return
            except Exception as exc:  # noqa: BLE001 — the agent forgot; say so
                print(f"ACP-RESUME-LOST {self.o.agent.name} {known}: {exc}", flush=True)
        fresh = await self._conn.new_session(cwd=self.o.cwd, mcp_servers=[])
        self.session_id = fresh.session_id
        await self._mirror("session", {"agent_session": fresh.session_id,
                                       "replaced": known, "load_supported": self._can_load})

    async def query(self, payload: Any) -> None:
        assert self._conn is not None
        blocks = await collect_blocks(payload)
        await self._mirror("prompt", {"blocks": [b.model_dump(mode="json", exclude_none=True)
                                                 for b in blocks]})
        self.bridge.armed = True
        self._task = asyncio.create_task(
            self._conn.prompt(session_id=self.session_id, prompt=blocks))

    async def receive_response(self) -> Any:
        assert self._task is not None
        queue = self.bridge.queue
        while True:
            take = asyncio.ensure_future(queue.get())
            done, _ = await asyncio.wait({take, self._task}, return_when=asyncio.FIRST_COMPLETED)
            if take in done:
                yield take.result()
                continue
            take.cancel()
            while not queue.empty():
                yield queue.get_nowait()
            break
        self.bridge.armed = False
        response = self._task.result()
        await self._mirror("result", response.model_dump(mode="json", exclude_none=True))
        yield result_message(response, self.session_id, self.bridge.cost)

    async def __aexit__(self, *exc: Any) -> None:
        if self._task is not None and not self._task.done():
            self._task.cancel()
        if self._spawn is not None:
            await self._spawn.__aexit__(None, None, None)
