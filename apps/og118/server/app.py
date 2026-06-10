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
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel

from runner import build_runner
from tts import (
    DEFAULT_FORMAT,
    TTSNotConfiguredError,
    TTSProvider,
    TTSUpstreamError,
    TTSValidationError,
    build_provider,
    content_type_for,
    validate_request,
)

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

# Built once from the ambient env. None when OG118_TTS_* is unset/incomplete —
# the /tts/synthesize route turns that into an explicit 503, never a crash.
_tts_provider = build_provider()


def get_tts_provider() -> TTSProvider | None:
    """Dependency seam: returns the configured provider (or None). Overridable in
    tests via app.dependency_overrides so they never touch the network or need a
    real key."""
    return _tts_provider


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class TTSRequest(BaseModel):
    text: str
    voice: str | None = None
    response_format: str = DEFAULT_FORMAT
    speed: float = 1.0


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


@app.post("/tts/synthesize")
async def tts_synthesize(
    req: TTSRequest,
    _: None = Depends(require_access),
    provider: TTSProvider | None = Depends(get_tts_provider),
) -> Response:
    """Synthesize speech for `text` and return the raw audio blob.

    This is the backend gate the frontend's `VoiceAdapter.synthesize` needs — it
    returns audio bytes + a Content-Type so the consumer can build an
    `AudioSource`. Gated by the same single-user bearer as /chat/stream.

    Failure is explicit and secret-free:
      - provider unconfigured (OG118_TTS_* unset) -> 503 TTS_NOT_CONFIGURED
      - bad input (empty/too-long text, bad format/speed) -> 400 TTS_INVALID_REQUEST
      - provider/network error -> 502 TTS_UPSTREAM_ERROR
    No request/response carries any secret value.
    """
    if provider is None:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "TTS_NOT_CONFIGURED",
                "message": (
                    "TTS is not configured on this deployment. Set "
                    "OG118_TTS_ENDPOINT, OG118_TTS_API_KEY and OG118_TTS_DEPLOYMENT."
                ),
            },
        )

    try:
        validate_request(req.text, req.response_format, req.speed)
    except TTSValidationError as exc:
        raise HTTPException(
            status_code=400,
            detail={"code": "TTS_INVALID_REQUEST", "message": str(exc)},
        ) from None

    try:
        audio = await provider.synthesize(
            req.text,
            voice=req.voice or "",
            response_format=req.response_format,
            speed=req.speed,
        )
    except TTSNotConfiguredError as exc:
        raise HTTPException(
            status_code=503,
            detail={"code": "TTS_NOT_CONFIGURED", "message": str(exc)},
        ) from None
    except TTSUpstreamError as exc:
        # str(exc) is status-only / type-only by construction (see tts.py) — safe.
        raise HTTPException(
            status_code=502,
            detail={"code": "TTS_UPSTREAM_ERROR", "message": str(exc)},
        ) from None

    return Response(
        content=audio,
        media_type=content_type_for(req.response_format),
        headers={"Cache-Control": "private, max-age=0, no-store"},
    )
