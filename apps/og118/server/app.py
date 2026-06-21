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

from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel

from fi_runner.rag_store import RagStoreClient
from runner import build_runner
from stt import (
    DEFAULT_UPLOAD_CONTENT_TYPE,
    STTNotConfiguredError,
    STTProvider,
    STTUpstreamError,
    STTValidationError,
)
from stt import build_provider as build_stt_provider
from stt import safe_filename_for_mime, validate_audio, validate_mime
from tts import (
    DEFAULT_FORMAT,
    TTSNotConfiguredError,
    TTSProvider,
    TTSUpstreamError,
    TTSValidationError,
    content_type_for,
    validate_request,
)
from tts import build_provider as build_tts_provider

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

# Built once from the ambient env. None when OG118_TTS_* / OG118_STT_* is
# unset/incomplete — the voice routes turn that into an explicit 503, never a
# crash.
_tts_provider = build_tts_provider()
_stt_provider = build_stt_provider()


def get_tts_provider() -> TTSProvider | None:
    """Dependency seam: returns the configured provider (or None). Overridable in
    tests via app.dependency_overrides so they never touch the network or need a
    real key."""
    return _tts_provider


def get_stt_provider() -> STTProvider | None:
    """Dependency seam for STT: returns the configured provider (or None).
    Overridable in tests via app.dependency_overrides, exactly like its TTS
    twin, so the contract is exercised without the network or a real key."""
    return _stt_provider


_rag_store: RagStoreClient | None = None


def get_rag_store() -> RagStoreClient:
    """Dependency seam: the project corpus store (ingest/search), built lazily on
    first use and reused — HDF5 loads its on-disk index at construction. Backend +
    path resolve from FI_RAG_BACKEND / FI_RAG_STORE_PATH (hdf5 + hashing zero-model
    by default). Overridable in tests via app.dependency_overrides so they hit a
    tmp store, never prod."""
    global _rag_store
    if _rag_store is None:
        _rag_store = RagStoreClient()
    return _rag_store


class HistoryMessage(BaseModel):
    """One prior turn the client replays for continuity. UNTRUSTED — re-sanitized
    by fi_runner.sanitize_history (role allowlist, caps) before it folds into the
    prompt. It is conversational context, never authorization."""

    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    # Client-supplied conversation history (og118 is local-first: the transcript
    # lives in the browser's IndexedDB and is replayed each turn). This is why
    # continuity survives an ACA replica recycle with NO server-side store — the
    # durable source of truth is the client, not the backend's RAM.
    history: list[HistoryMessage] | None = None
    # Active project's corpus for this turn (Projects canary). corpus_id = the
    # local-first project id the user selected; absent means no active project.
    # It binds via fi_runner.active_corpus_binding so the agent scopes its
    # rag_store search to THIS corpus. Pre-Gate-3 it is NOT authorization — a
    # shared bearer guards the route; ownership lands with auth (PROJ-ACCOUNT).
    corpus_id: str | None = None


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
            history = [m.model_dump() for m in req.history] if req.history else None
            context = {"corpus_id": req.corpus_id} if req.corpus_id else None
            async for event in _runner.run_stream(
                req.message,
                session_id=req.session_id,
                request_id=request_id,
                history=history,
                context=context,
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


class TranscriptResponse(BaseModel):
    text: str


@app.post("/stt/transcribe")
async def stt_transcribe(
    audio: UploadFile = File(...),
    _: None = Depends(require_access),
    provider: STTProvider | None = Depends(get_stt_provider),
) -> TranscriptResponse:
    """Transcribe one recorded audio chunk and return its text.

    This is the backend gate the frontend's `VoiceAdapter.transcribe` needs — it
    accepts a multipart audio upload and returns `{text}` so the consumer's
    `useDictation` can accumulate the transcript. Gated by the same single-user
    bearer as /chat/stream and /tts/synthesize.

    Failure is explicit and secret-free, mirroring /tts/synthesize:
      - provider unconfigured (OG118_STT_* unset) -> 503 STT_NOT_CONFIGURED
      - bad input (empty/too-large audio) -> 400 STT_INVALID_REQUEST
      - provider/network error -> 502 STT_UPSTREAM_ERROR
    No request/response carries any secret value.
    """
    if provider is None:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "STT_NOT_CONFIGURED",
                "message": (
                    "STT is not configured on this deployment. Set "
                    "OG118_STT_ENDPOINT, OG118_STT_API_KEY and OG118_STT_DEPLOYMENT."
                ),
            },
        )

    data = await audio.read()
    content_type = audio.content_type or DEFAULT_UPLOAD_CONTENT_TYPE
    try:
        validate_audio(data)
        validate_mime(content_type)
    except STTValidationError as exc:
        raise HTTPException(
            status_code=400,
            detail={"code": "STT_INVALID_REQUEST", "message": str(exc)},
        ) from None

    try:
        text = await provider.transcribe(
            data,
            filename=safe_filename_for_mime(content_type),
            content_type=content_type,
        )
    except STTNotConfiguredError as exc:
        raise HTTPException(
            status_code=503,
            detail={"code": "STT_NOT_CONFIGURED", "message": str(exc)},
        ) from None
    except STTUpstreamError as exc:
        # str(exc) is status-only / type-only by construction (see stt.py) — safe.
        raise HTTPException(
            status_code=502,
            detail={"code": "STT_UPSTREAM_ERROR", "message": str(exc)},
        ) from None

    return TranscriptResponse(text=text)


@app.post("/projects/{project_id}/upload")
async def upload_project_document(
    project_id: str,
    file: UploadFile = File(...),
    _: None = Depends(require_access),
    rag: RagStoreClient = Depends(get_rag_store),
) -> dict:
    """Ingest a text document into the project's corpus (corpus_id=project_id).

    Plain text in (txt/md): the bytes are decoded as UTF-8, chunked + persisted
    under the file's name. Binary/non-UTF-8 or empty → 400 (PDF/DOCX extraction is
    the caller's job). The agent's rag_store tools then search this corpus when the
    project is the active corpus (see fi_runner.active_corpus_binding). Auth-agnostic
    for now: gated by the same bearer speed-bump as the other routes, NOT tied to a
    user until Gate 3."""
    raw = await file.read()
    if not raw:
        raise HTTPException(
            status_code=400, detail={"code": "EMPTY_FILE", "message": "uploaded file is empty"}
        )
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400,
            detail={"code": "NOT_TEXT", "message": "file is not UTF-8 text; extract text before upload"},
        ) from None
    if not text.strip():
        raise HTTPException(
            status_code=400, detail={"code": "EMPTY_FILE", "message": "uploaded file has no text"}
        )
    doc_id = file.filename or "document.txt"
    # min_chunk_size lowered from fi-core's default (100 TOKENS): papelería docs
    # (inventory lists, short notes) are short and would otherwise yield 0 chunks.
    chunks = await rag.ingest(project_id, doc_id, text, min_chunk_size=20)
    return {"corpus_id": project_id, "doc_id": doc_id, "chunks": chunks}
