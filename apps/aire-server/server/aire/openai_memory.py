"""Memory without a Codex turn (#54): a ROUTED key on the OpenAI door remembers.

The ThinkPad's Stop judge calls `/openai/v1/chat/completions` up to 90 times an hour;
a Codex casita turn per verdict (25–50 s, serialized, on a 512 MB box) cannot carry
that, so the verdict stays on Azure and the casita's memory rides around it. Before
the relay, the corrections Bernard wrote into the casita (`stop-judge-correct.py`,
through the message door) are read and appended to the system message; after it,
the verdict is appended to the casita's own log with the pen Codex uses
(`acp_mirror`), in a session per local day. Both halves are best-effort: a read
past its budget or a failed write relays the turn exactly as it came.

Which key maps to which casita is CONTENT (`prompts/openai-memory-routes.json`),
so a re-provisioned box routes the same with nothing set by hand; an unrouted key's bytes are untouched.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from . import acp_mirror
from .engine import Engine, memory_tool
from .gateway_mirror import ResponseTap
from .names import clean

ROUTES_FILE = Path(__file__).resolve().parent / "prompts" / "openai-memory-routes.json"
PROVIDER = "openai"
READ_BUDGET_S = 1.5
ASKED_CHARS = 4000
MEXICO_CITY = timezone(timedelta(hours=-6))  # no daylight saving since 2022
_CACHE: dict[str, Any] = {"mtime": None, "data": {}}
_pending: set[asyncio.Task[None]] = set()


@dataclass(frozen=True)
class Route:
    project: str
    project_key: str
    session_id: str


def content() -> dict[str, Any]:
    """The routes file, re-read when it changes ([[prompts-as-content-not-code]])."""
    mtime = ROUTES_FILE.stat().st_mtime
    if _CACHE["mtime"] != mtime:
        _CACHE["data"] = json.loads(ROUTES_FILE.read_text(encoding="utf-8"))
        _CACHE["mtime"] = mtime
    return _CACHE["data"]


def route_for(nickname: str) -> Route | None:
    """The casita a key remembers in, keyed exactly as the message door keys it."""
    try:
        project = content().get("routes", {}).get(nickname)
        if not project:
            return None
        day = datetime.now(MEXICO_CITY).strftime("%Y-%m-%d")
        key = Engine.session_key(clean("project", project), day)
        return Route(project, key["project_key"], key["session_id"])
    except Exception as exc:  # noqa: BLE001 — a broken route relays as if unrouted
        print(f"OPENAI-MEMORY-NO-ROUTE {nickname}: {type(exc).__name__}: {exc}", flush=True)
        return None


def brief(text: str) -> str:
    """One correction as one line: when, what was denied, what Bernard said."""
    head, _, tail = text.partition("\nWhat you denied: ")
    denied, _, said = tail.partition("\nHis correction: ")
    said = said.split("\nThis is the record", 1)[0].strip()
    if not said:
        return "- " + text[:800]
    when = head.split("When: ", 1)[-1].split(". ", 1)[0] if "When: " in head else "?"
    return f"- {when} denied: {denied.strip()[:300]} | Bernard: {said[:500]}"


def inject(body: bytes, block: str) -> bytes:
    """The block appended to the system message (one is opened if none exists)."""
    parsed = json.loads(body)
    messages = parsed.get("messages") if isinstance(parsed, dict) else None
    if not isinstance(messages, list):
        return body
    system = next((m for m in messages if isinstance(m, dict) and m.get("role") in ("system", "developer")), None)
    if system is None:
        messages.insert(0, {"role": "system", "content": block})
    elif isinstance(system.get("content"), list):
        system["content"].append({"type": "text", "text": block})
    else:
        system["content"] = f"{system.get('content') or ''}\n\n{block}"
    return json.dumps(parsed, ensure_ascii=False).encode("utf-8")


async def remind(route: Route, body: bytes) -> bytes:
    """The body with the casita's corrections in it, or the body as it came."""
    try:
        conf = content()
        texts = await asyncio.wait_for(memory_tool.marked(
            route.project_key, conf["marker"], int(conf.get("limit", 10)), int(READ_BUDGET_S * 1000)),
            READ_BUDGET_S)
        if not texts:
            return body
        return inject(body, "\n".join([conf["header"], *(brief(t) for t in texts)]))
    except Exception as exc:  # noqa: BLE001 — memory never breaks the judge
        print(f"OPENAI-MEMORY-SKIPPED {route.project}: {type(exc).__name__}: {exc}", flush=True)
        return body


def asked(body: bytes) -> str:
    """The last user message's text, as the caller sent it (never the injected block)."""
    try:
        messages = json.loads(body).get("messages") or []
        user = [m for m in messages if isinstance(m, dict) and m.get("role") == "user"]
        text = user[-1].get("content") if user else ""
        if isinstance(text, list):
            text = "\n".join(p.get("text", "") for p in text if isinstance(p, dict))
        return str(text or "")[:ASKED_CHARS]
    except Exception:  # noqa: BLE001 — a body that is not chat still leaves a row
        return ""


def answer(message: Any) -> str:
    try:
        return str(message["choices"][0]["message"]["content"] or "")
    except (KeyError, IndexError, TypeError):
        return str((message or {}).get("output_text") or "") if isinstance(message, dict) else ""


async def remember(route: Route, question: str, reply: str, status: int) -> None:
    for kind, entry in (("request", {"text": question}), ("response", {"text": reply, "status": status})):
        await acp_mirror.append(route.project_key, route.session_id, PROVIDER, None, kind, entry)


class RememberingTap(ResponseTap):
    """The door's tap, plus the verdict appended to the casita — off the response's path."""

    def __init__(self, route: Route, body: bytes, *args: Any) -> None:
        super().__init__(*args)
        self.route, self.question = route, asked(body)

    async def finish(self) -> None:
        if self.done:
            return
        await super().finish()
        reply = answer(self.assembler(bytes(self.raw), self.content_type))
        task = asyncio.create_task(remember(self.route, self.question, reply, self.status))
        _pending.add(task)
        task.add_done_callback(_pending.discard)
