"""The Codex backend — OpenAI's own headless client, `codex exec --json`, on the
ChatGPT plan a `codex login` left on this box (#52). Every turn Bernard runs
through it spends the plan's quota and no metered token; it is the road the
official `@openai/codex-sdk` drives underneath, OpenAI's sanctioned surface,
never a scrape of chatgpt.com.

Measured 2026-10-26 against codex-cli 0.164.0: a turn is ONE process (`exec`
for a fresh thread, `exec resume <thread>` after that), events arrive as JSON
lines, and the thread lives in the box's `~/.codex` like a Claude session lives
in its store — so the daemon mirrors every event through `acp_mirror` (the pen
is the same, only the agent differs) and remembers which thread answers to
which AIRE session. A resume the box cannot honour (`no rollout found`, exit 1)
opens a fresh thread LOUDLY, the ACP backend's cold-resume law.

The ACP road was tried first and is dead for now: `codex-acp` 0.16.0 bundles
codex-core 0.137 and the backend answers *"gpt-6-astra requires a newer version
of Codex"* — re-measure when Zed ships a newer adapter."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

from .. import acp_mirror
from .acp_messages import ResultMessage
from .codex_events import item_messages, prompt_and_images, result
from .codex_options import NAME, CodexOptions, build_options, command, enabled
from .codex_process import CodexRun

__all__ = ["NAME", "CodexOptions", "build_options", "command", "enabled", "client"]
CREDENTIALS = "codex"  # the rotor chain its turns ride (#53): the plan's CODEX_HOME, then a metered CODEX_API_KEY


def client(options: CodexOptions) -> "CodexClient":
    return CodexClient(options)


class CodexClient:
    def __init__(self, options: CodexOptions) -> None:
        self.o = options
        self.thread: str | None = None
        self.spent = 0.0  # cumulative, like the SDK's total_cost_usd: the ledger banks the delta
        self._run: Any = None
        self._fresh = False  # the next run opens a new thread even though one is remembered
        self._opened: set[str] = set()
        self._prompt = ""
        self._images: list[tuple[bytes, str]] = []

    async def __aenter__(self) -> "CodexClient":
        self.thread = await acp_mirror.agent_session(self.o.project_key, self.o.session_uuid, NAME)
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self._close()

    async def _close(self) -> None:
        if self._run is not None:
            await self._run.close()
            self._run = None

    async def _mirror(self, kind: str, entry: dict[str, Any]) -> None:
        await acp_mirror.append(self.o.project_key, self.o.session_uuid, NAME, self.thread, kind, entry)

    def _loud(self, what: str, detail: str) -> None:
        print(f"{what} {self.o.project_key}/{self.o.session_uuid}: {detail[-400:]}", flush=True)

    async def _start(self) -> None:
        await self._close()
        self._run = CodexRun(self.o.command, self.o.cwd, self.o.model, self.o.effort, self.o.allow_tools,
                             self._prompt, self._images, None if self._fresh else self.thread, self.o.env)
        self._fresh = False
        await self._run.start()

    async def query(self, payload: Any) -> None:
        self._prompt, self._images = await prompt_and_images(payload)
        self._opened = set()
        await self._mirror("prompt", {"text": self._prompt, "images": len(self._images),
                                      "resume": self.thread})
        await self._start()

    async def receive_response(self) -> AsyncIterator[Any]:
        """The process's JSON lines as drain messages until the turn closes; a
        silent exit is an `error_exit_<code>` result, never a lying success."""
        seen_thread = False
        async for line in self._run.lines():
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if event.get("type") == "thread.started":
                seen_thread = True
                await self._on_thread(event["thread_id"])
                continue
            for message in await self._on_event(event):
                yield message
            if event.get("type") in ("turn.completed", "turn.failed"):
                await self._close()
                return
        code, tail = await self._run.finish()
        async for message in self._on_exit(code, tail, seen_thread):
            yield message

    async def _on_exit(self, code: int, tail: str, seen_thread: bool) -> AsyncIterator[Any]:
        """No closing event came. A resume the box has no rollout for reopens
        fresh and says so (CODEX-RESUME-LOST); anything else is CODEX-EXIT."""
        if self.thread and not seen_thread and "no rollout found" in tail:
            self._loud("CODEX-RESUME-LOST", f"thread {self.thread} has no rollout here; opening a fresh one")
            self._fresh = True
            await self._start()
            async for message in self.receive_response():
                yield message
            return
        await self._close()
        self._loud("CODEX-EXIT", f"exit {code}: {tail.strip()}")
        await self._mirror("result", {"stop_reason": f"exit_{code}", "stderr": tail})
        yield ResultMessage(subtype=f"error_exit_{code}", session_id=self.thread or "")

    async def _on_thread(self, thread_id: str) -> None:
        if thread_id == self.thread:
            return
        replaced, self.thread = self.thread, thread_id
        await self._mirror("session", {"agent_session": thread_id, "replaced": replaced,
                                       "load_supported": True})

    async def _on_event(self, event: dict[str, Any]) -> list[Any]:
        kind = event.get("type", "")
        if kind in ("turn.completed", "turn.failed"):
            entry, message = result(event, self.thread, self.o.model)
            if kind == "turn.failed":
                self._loud("CODEX-TURN-FAILED", entry["error"])
            else:
                self.spent += message.total_cost_usd or 0.0
                message.total_cost_usd = self.spent
            await self._mirror("result", entry)
            return [message]
        if kind == "error":
            self._loud("CODEX-ERROR", event.get("message", ""))
            await self._mirror(kind, event)
            return []
        item = event.get("item") or {}
        if not item:
            return []
        await self._mirror(kind, item)
        if item.get("type") == "error":
            self._loud("CODEX-ITEM-ERROR", item.get("message", ""))
        return item_messages(kind, item, self.o.model, self._opened)
