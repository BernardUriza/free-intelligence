"""og118 server — FastAPI + SSE over fi-runner's run_stream.

POST /chat/stream  {message, session_id?}  ->  text/event-stream of fi-runner
NATIVE events (open / text / tool_call / plan / step_* / plan_rejected / result
/ error / done). The frontend hook maps these onto core's ChatHook /
AgentStreamEvent — the backend stays transport-honest and does NOT pre-shape to
the core union (that mapping is the contract being validated from the consumer).
"""

from __future__ import annotations

import dataclasses
import hmac
import json
import logging
import os
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from runner import build_runner

logger = logging.getLogger("og118")

# --- Config from env (no secrets in code; cloud injects these) ----------------
# Comma-separated allowed CORS origins; defaults to the local Next dev server so
# nothing changes for local work. Cloud sets the SWA origin.
_DEFAULT_ORIGINS = "http://localhost:3000,http://127.0.0.1:3000"
_ALLOWED_ORIGINS = [
    o.strip() for o in os.getenv("OG118_ALLOWED_ORIGINS", _DEFAULT_ORIGINS).split(",") if o.strip()
]

# Single-user access gate. UNSET = open (local dev convenience). SET = every
# /chat/stream call must carry `Authorization: Bearer <token>`. Cloud MUST set
# it — a public, ungated backend would let anyone burn the API-key billing.
_ACCESS_TOKEN = os.getenv("OG118_ACCESS_TOKEN")

@asynccontextmanager
async def _lifespan(_: FastAPI) -> AsyncIterator[None]:
    if not _ACCESS_TOKEN:
        logger.warning(
            "OG118_ACCESS_TOKEN is unset: /chat/stream is OPEN (no auth). "
            "Fine for local dev; MUST be set in any cloud/staging deploy."
        )
    yield


app = FastAPI(title="og118 server", version="0.0.0", lifespan=_lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


def require_access(authorization: str | None = Header(default=None)) -> None:
    """Gate /chat/stream behind a bearer token when OG118_ACCESS_TOKEN is set.

    Unset → no gate (local dev). Set → constant-time compare against
    `Bearer <token>`; 401 on mismatch/absence. /health stays ungated so Azure
    can probe it. NOTE: this is a single-user speed-bump, not real auth — a
    network/identity gate is still required for stable production.
    """
    if not _ACCESS_TOKEN:
        return
    expected = f"Bearer {_ACCESS_TOKEN}"
    if not authorization or not hmac.compare_digest(authorization, expected):
        raise HTTPException(status_code=401, detail="invalid or missing access token")


_runner = build_runner()


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


def _to_jsonable(value: object) -> object:
    """fi-runner events carry dataclasses (ToolCall, TurnResult). Convert them so
    the native shape survives as JSON; anything else falls back to str at dump."""
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return dataclasses.asdict(value)
    return value


def _sse(event: dict) -> str:
    payload = {k: _to_jsonable(v) for k, v in event.items()}
    return f"data: {json.dumps(payload, default=str)}\n\n"


@app.get("/health")
async def health() -> dict:
    return {"ok": True}


@app.post("/chat/stream")
async def chat_stream(
    req: ChatRequest, _: None = Depends(require_access)
) -> StreamingResponse:
    async def generate() -> AsyncIterator[str]:
        request_id = uuid.uuid4().hex[:12]
        yield _sse({"type": "open", "request_id": request_id})
        try:
            async for event in _runner.run_stream(
                req.message, session_id=req.session_id, request_id=request_id
            ):
                yield _sse(event)
        except Exception as exc:  # surface as a stream event, never a 500 mid-stream
            yield _sse({"type": "error", "message": str(exc)})
        yield _sse({"type": "done"})

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
