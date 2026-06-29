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
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel

from fi_runner.auth import (
    AuthConfig,
    Auth0Validator,
    Principal,
    legacy_principal,
    make_auth_dependency,
)
from fi_runner.rag_store import RagStoreClient
from projects import ProjectRegistry
from runner import build_runner
from external_engine import stream_external_turn
from fi_runner import Runner
from elements_registry import Element, get_registry
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

# Auth gate. OG118_AUTH_MODE picks the level (default `bearer` = today's behavior,
# nothing changes until explicitly flipped — the lockout-prevention guarantee):
#   bearer → legacy shared OG118_ACCESS_TOKEN speed-bump (synthetic identity)
#   dual   → accept a valid Auth0 JWT OR the legacy bearer (zero-downtime cutover)
#   auth0  → Auth0 JWT only
# The Auth0 validation + dual-accept come from the fi_runner.auth framework
# primitive (the og118-Gate-3 canary). `principal.sub` is the account_id that
# owns projects (PROJ-ACCOUNT-1).
_ACCESS_TOKEN = os.getenv("OG118_ACCESS_TOKEN")
_AUTH_MODE = os.getenv("OG118_AUTH_MODE", "bearer").lower()
_AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN")
_AUTH0_AUDIENCE = os.getenv("AUTH0_AUDIENCE")
_auth0_validator = (
    Auth0Validator(AuthConfig(domain=_AUTH0_DOMAIN, audience=_AUTH0_AUDIENCE))
    if _AUTH0_DOMAIN and _AUTH0_AUDIENCE
    else None
)


def _bearer_dep(authorization: str | None = Header(default=None)) -> Principal:
    """Legacy speed-bump: open when no token is set (local dev), else require the
    shared bearer. Identity is the synthetic legacy principal."""
    if _ACCESS_TOKEN:
        expected = f"Bearer {_ACCESS_TOKEN}"
        if not authorization or not hmac.compare_digest(authorization, expected):
            raise HTTPException(status_code=401, detail="invalid or missing access token")
    return legacy_principal()


def _build_principal_impl() -> Callable[..., Principal]:
    if _AUTH_MODE == "bearer":
        return _bearer_dep
    if _AUTH_MODE == "dual":
        return make_auth_dependency(_auth0_validator, legacy_bearer=_ACCESS_TOKEN)
    if _AUTH_MODE == "auth0":
        return make_auth_dependency(_auth0_validator)
    raise RuntimeError(f"OG118_AUTH_MODE must be bearer|dual|auth0 (got {_AUTH_MODE!r})")


_principal_impl = _build_principal_impl()


@asynccontextmanager
async def _lifespan(_: FastAPI) -> AsyncIterator[None]:
    if _AUTH_MODE == "bearer" and not _ACCESS_TOKEN:
        logger.warning(
            "OG118_AUTH_MODE=bearer with OG118_ACCESS_TOKEN unset: routes are OPEN. "
            "Fine for local dev; MUST set the token (or a real mode) in any cloud deploy."
        )
    if _AUTH_MODE in ("dual", "auth0") and _auth0_validator is None:
        logger.error(
            "OG118_AUTH_MODE=%s but AUTH0_DOMAIN/AUTH0_AUDIENCE are unset — every "
            "request would 401. Set them or revert to bearer mode.", _AUTH_MODE
        )
    yield


app = FastAPI(title="og118 server", version="0.0.0", lifespan=_lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_principal(authorization: str | None = Header(default=None)) -> Principal:
    """The authenticated caller for a request, per OG118_AUTH_MODE. Overridable
    in tests via app.dependency_overrides (like get_rag_store). `principal.sub`
    is the account_id used for project ownership."""
    return _principal_impl(authorization=authorization)


_runner = build_runner()

# Elemento runners (OG118-ELEMENTS-ADR-1): an active element swaps ONLY the
# persona. The base runner serves "no element". Per-element runners are built
# lazily from the registry and cached by canonical id.
_element_runners: dict[str, Runner] = {}


def _runner_and_element(element_token: str | None) -> tuple[Runner, Element | None]:
    """Resolve (Runner, Element) for this turn. Unknown/blank/non-active → the base
    og118 runner + None (the turn is byte-identical to no-element)."""
    el = get_registry().resolve(element_token)
    if el is None or not el.is_active:
        return _runner, None
    # External elements run on a remote engine (the chat_stream external branch),
    # so no local runner is built — return the base runner as an unused placeholder.
    if el.engine_binding is not None and el.engine_binding.is_external:
        return _runner, el
    cached = _element_runners.get(el.id)
    if cached is None:
        cached = build_runner(persona_text=get_registry().composed_persona(el))
        _element_runners[el.id] = cached
    return cached, el


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


_project_registry: ProjectRegistry | None = None


def get_project_registry() -> ProjectRegistry:
    """Dependency seam: the server-authoritative project↔owner↔corpus map (JSON
    on the Azure Files volume). Path from OG118_PROJECT_REGISTRY_PATH, defaulting
    next to FI_RAG_STORE_PATH. Overridable in tests via app.dependency_overrides
    so they hit a tmp registry, never prod."""
    global _project_registry
    if _project_registry is None:
        default = os.path.join(
            os.path.dirname(os.getenv("FI_RAG_STORE_PATH", "/opt/fi/data/fi_rag_store.h5")),
            "projects.json",
        )
        _project_registry = ProjectRegistry(os.getenv("OG118_PROJECT_REGISTRY_PATH", default))
    return _project_registry


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
    # Active "elemento" for this turn (OG118-ELEMENTS-ADR-1). A token the registry
    # resolves (slug/symbol/atomic number/alias, e.g. "oxigeno"/"O"/"8"); an active
    # element swaps the persona (Vultur for Oxígeno), nothing else. Absent/unknown/
    # non-active → the base og118 companion persona.
    element: str | None = None


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


@app.get("/elements")
async def list_elements() -> dict:
    """The active "elementos" the UI selector offers (OG118-ELEMENTS-ADR-1).

    Active-only by design: the 117 empty/reserved slots are catalog, not product —
    surfacing them would read as an unfinished roster. Public on purpose: this is
    names/symbols, never the persona prompts, so it carries nothing the bearer gate
    protects and it must render before the user pastes a token."""
    reg = get_registry()
    return {
        "elements": [
            {
                "id": e.id,
                "atomicNumber": e.atomic_number,
                "symbol": e.symbol,
                "slug": e.slug,
                "displayName": e.display_name,
                "displayLabel": e.display_label,
                "status": e.status,
                "aliases": list(e.aliases),
            }
            for e in reg.elements
            if e.is_active
        ]
    }


@app.post("/chat/stream")
async def chat_stream(
    req: ChatRequest,
    principal: Principal = Depends(get_principal),
    registry: ProjectRegistry = Depends(get_project_registry),
) -> StreamingResponse:
    # If a corpus is bound this turn, the caller must OWN it — turns corpus_id
    # from client-asserted into server-validated (no cross-account corpus reads).
    # Skipped for the legacy single shared account (bearer mode): there is one
    # tenant, ownership is moot, and pre-registry corpora keep working.
    if req.corpus_id and not principal.is_legacy_bearer and not registry.owns(req.corpus_id, principal.sub):
        raise HTTPException(status_code=404, detail="project not found")

    runner, element = _runner_and_element(req.element)
    external = element is not None and element.engine_binding is not None and element.engine_binding.is_external

    async def generate() -> AsyncIterator[str]:
        request_id = uuid.uuid4().hex[:12]
        yield _sse({"type": "open", "request_id": request_id})
        # Surface the active element so the glass-box trace shows WHO answered
        # (the ADR's E2E criterion). Absent when no active element is selected.
        if element is not None:
            yield _sse({"type": "element", "element": {"id": element.id, "label": element.display_label}})
        # ENGINE-BINDING-ADR-1: an external element runs on its own live engine, not
        # og118's runner. Proxy the turn and surface the answer (single-shot, no
        # local plan/step trace). og118's session_id keys the engine's context.
        if external:
            assert element is not None and element.engine_binding is not None
            user_id = None if principal.is_legacy_bearer else principal.sub
            async for ev in stream_external_turn(
                persona_id=element.engine_binding.persona_id,
                user_text=req.message,
                session_uuid=req.session_id,
                user_id=user_id,
            ):
                yield _sse(ev)
            yield _sse({"type": "done"})
            return
        try:
            history = [m.model_dump() for m in req.history] if req.history else None
            context = {"corpus_id": req.corpus_id} if req.corpus_id else None
            async for event in runner.run_stream(
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
    _: Principal = Depends(get_principal),
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
    _: Principal = Depends(get_principal),
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


class ProjectCreateRequest(BaseModel):
    # Only the display name is client-supplied. The corpus_id is NOT — minting it
    # server-side is the privacy boundary (a client-chosen id could land on another
    # project's corpus). Any extra field (e.g. a client-sent project_id) is dropped
    # by pydantic, which is exactly the invariant.
    name: str | None = None


@app.post("/projects")
async def create_project(
    req: ProjectCreateRequest,
    principal: Principal = Depends(get_principal),
    registry: ProjectRegistry = Depends(get_project_registry),
) -> dict:
    """Mint a project + its corpus_id SERVER-SIDE, OWNED by the caller's account
    (PROJ-ACCOUNT-1). The client never decides the corpus_id; the owner (account_id
    = principal.sub) is stamped server-side so only the owner can reach it."""
    project = registry.create(principal.sub, req.name)
    return {"project_id": project["id"], "name": project["name"]}


@app.get("/projects")
async def list_projects(
    principal: Principal = Depends(get_principal),
    registry: ProjectRegistry = Depends(get_project_registry),
) -> dict:
    """The caller's projects (server-authoritative, filtered by owner account)."""
    return {"projects": registry.list_for(principal.sub)}


@app.delete("/projects/{project_id}")
async def delete_project(
    project_id: str,
    principal: Principal = Depends(get_principal),
    registry: ProjectRegistry = Depends(get_project_registry),
    rag: RagStoreClient = Depends(get_rag_store),
) -> dict:
    """Delete a project the caller owns AND its corpus (no orphaned consultable
    docs). 404 if missing or not owned (no existence probing)."""
    if not registry.delete(project_id, principal.sub):
        raise HTTPException(status_code=404, detail="project not found")
    await rag.delete_corpus(project_id)
    return {"deleted": project_id}


@app.post("/projects/{project_id}/upload")
async def upload_project_document(
    project_id: str,
    file: UploadFile = File(...),
    principal: Principal = Depends(get_principal),
    registry: ProjectRegistry = Depends(get_project_registry),
    rag: RagStoreClient = Depends(get_rag_store),
) -> dict:
    """Ingest a text document into the project's corpus (corpus_id=project_id).

    The caller must OWN the project (404 otherwise — no existence probing). Plain
    text in (txt/md): the bytes are decoded as UTF-8, chunked + persisted under the
    file's name. Binary/non-UTF-8 or empty → 400 (PDF/DOCX extraction is the
    caller's job). The agent's rag_store tools then search this corpus when the
    project is the active corpus (see fi_runner.active_corpus_binding)."""
    # Ownership enforced for real accounts; the legacy single shared account
    # (bearer mode) skips it so pre-registry corpora keep working.
    if not principal.is_legacy_bearer and not registry.owns(project_id, principal.sub):
        raise HTTPException(status_code=404, detail="project not found")
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
