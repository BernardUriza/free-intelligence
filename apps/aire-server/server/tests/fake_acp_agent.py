"""A tiny ACP agent for the backend's tests — the stdio is real, the model is
not. It echoes `pong: <prompt>` in two chunks, asks permission before a tool
when the prompt says "tool", reports a cost when it says "cost", and keeps its
memory in FAKE_ACP_STORE so a second process can `session/load` it — which is
exactly the warm/cold resume seam the backend has to get right."""

from __future__ import annotations

import asyncio
import json
import os
import uuid
from pathlib import Path
from typing import Any

import acp
from acp import RequestError, schema

STORE = Path(os.environ.get("FAKE_ACP_STORE", "/nonexistent"))
OPTIONS = [schema.PermissionOption(option_id="y", name="Allow", kind="allow_once"),
           schema.PermissionOption(option_id="n", name="Reject", kind="reject_once")]


def _load(sid: str) -> list[str] | None:
    path = STORE / f"{sid}.json"
    return json.loads(path.read_text()) if path.exists() else None


def _save(sid: str, history: list[str]) -> None:
    STORE.mkdir(parents=True, exist_ok=True)
    (STORE / f"{sid}.json").write_text(json.dumps(history))


class FakeAgent:
    def __init__(self) -> None:
        self.conn: Any = None

    def on_connect(self, conn: Any) -> None:
        self.conn = conn

    async def initialize(self, protocol_version: int, **_: Any) -> schema.InitializeResponse:
        return schema.InitializeResponse(protocol_version=acp.PROTOCOL_VERSION,
                                         agent_capabilities=schema.AgentCapabilities(load_session=True))

    async def new_session(self, cwd: str, **_: Any) -> schema.NewSessionResponse:
        sid = str(uuid.uuid4())
        _save(sid, [])
        return schema.NewSessionResponse(session_id=sid)

    async def load_session(self, cwd: str, session_id: str, **_: Any) -> schema.LoadSessionResponse:
        history = _load(session_id)
        if history is None:
            raise RequestError(-32001, f"unknown session {session_id}")
        for text in history:
            await self.conn.session_update(session_id=session_id, update=acp.update_agent_message_text(text))
        return schema.LoadSessionResponse()

    async def prompt(self, session_id: str, prompt: list[Any], **_: Any) -> schema.PromptResponse:
        text = " ".join(getattr(b, "text", None) or f"<{b.type}>" for b in prompt)
        if "tool" in text:
            await self._tool(session_id, text)
        for piece in ("pong: ", text):
            await self.conn.session_update(session_id=session_id, update=acp.update_agent_message_text(piece))
        if "cost" in text:
            await self.conn.session_update(session_id=session_id, update=schema.UsageUpdate(
                session_update="usage_update", used=5, size=100,
                cost=schema.Cost(amount=0.0042, currency="USD")))
        _save(session_id, (_load(session_id) or []) + [f"pong: {text}"])
        return schema.PromptResponse(stop_reason="end_turn", usage=schema.Usage(
            total_tokens=5, input_tokens=3, output_tokens=2, cached_read_tokens=1, cached_write_tokens=0))

    async def _tool(self, session_id: str, text: str) -> None:
        await self.conn.session_update(session_id=session_id, update=acp.start_tool_call(
            "t1", "fake_tool", status="pending", raw_input={"q": text}))
        verdict = await self.conn.request_permission(
            session_id=session_id, tool_call=schema.ToolCallUpdate(tool_call_id="t1", title="fake_tool"),
            options=OPTIONS)
        allowed = getattr(verdict.outcome, "option_id", None) == "y"
        await self.conn.session_update(session_id=session_id, update=acp.update_tool_call(
            "t1", status="completed" if allowed else "failed"))

    async def cancel(self, session_id: str, **_: Any) -> None:
        return None

    def __getattr__(self, name: str) -> Any:
        if name.startswith("_"):
            raise AttributeError(name)

        async def refuse(*_: Any, **__: Any) -> Any:
            raise RequestError.method_not_found(name)
        return refuse


if __name__ == "__main__":
    asyncio.run(acp.run_agent(FakeAgent()))
