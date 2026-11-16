"""POST /chat/stream — one turn as server-sent events, and its explicit stop.

The stream carries fi-runner's NATIVE events (open / text / tool_call / plan /
step_* / plan_rejected / result / error / done); the client maps them.
"""

from __future__ import annotations

import asyncio
import base64
import binascii
import dataclasses
import json
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator

from fi_runner.auth import Principal
from fi_runner.rag_store import RagStoreClient
import deps
import detached_turn
import push
from conversations import utc_now_iso
from deps import (
    RunnerSelector,
    get_principal,
    get_project_registry,
    get_rag_store,
    get_runner_selector,
    logger,
    proyectos_activos,
)
from external_engine import late_message, stream_external_turn
from projects import ProjectRegistry, turn_context
from runner import AIRE_CHAT_PROJECT, aire_project_for_chat, background_tool_spec

router = APIRouter()

async def _announce(owner: str, conversation_id: str, message: dict) -> None:
    """The late answer is in the record; say so on the account's phones. Never raises."""
    try:
        author = message.get("author")
        title = (author.get("name") if isinstance(author, dict) else None) or "og118"
        accepted = await push.notify(deps.get_device_store(), owner, title, message.get("content") or "", conversation_id)
        logger.info("late answer announced: devices_accepted=%d", accepted)
    except Exception:
        logger.exception("late answer was stored but not announced")


class HistoryMessage(BaseModel):
    """One prior turn the client replays for continuity. UNTRUSTED — re-sanitized
    by fi_runner.sanitize_history (role allowlist, caps) before it folds into the
    prompt. It is conversational context, never authorization."""

    role: str
    content: str


# Vision input caps (OG118-IMAGE-UPLOAD-1). Anthropic's per-image API limit is
# 5 MB decoded; the composer downscales before encoding, so a compliant client
# never hits these — they exist for the hostile/buggy one. base64 inflates 4/3,
# so the string cap is the decoded cap ×4/3 (plus padding slack).
MAX_IMAGES_PER_MESSAGE = 4
MAX_IMAGE_BYTES = 5 * 1024 * 1024
_MAX_IMAGE_B64_CHARS = (MAX_IMAGE_BYTES * 4) // 3 + 4
ALLOWED_IMAGE_MEDIA_TYPES = frozenset({"image/jpeg", "image/png", "image/webp", "image/gif"})


class ChatImage(BaseModel):
    """One image attached to the current turn (base64, no data: prefix).
    Validated at the boundary so a bad payload dies as a 422 here, never as an
    opaque upstream engine error mid-stream."""

    media_type: str
    data: str

    @field_validator("media_type")
    @classmethod
    def _known_media_type(cls, v: str) -> str:
        if v not in ALLOWED_IMAGE_MEDIA_TYPES:
            raise ValueError(f"unsupported image media_type {v!r}; use one of {sorted(ALLOWED_IMAGE_MEDIA_TYPES)}")
        return v

    @field_validator("data")
    @classmethod
    def _bounded_base64(cls, v: str) -> str:
        if not v:
            raise ValueError("image data is empty")
        if len(v) > _MAX_IMAGE_B64_CHARS:
            raise ValueError(f"image exceeds the {MAX_IMAGE_BYTES // (1024 * 1024)} MB limit")
        try:
            base64.b64decode(v, validate=True)
        except (binascii.Error, ValueError):
            raise ValueError("image data is not valid base64") from None
        return v


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
    # Images attached to THIS turn's message (OG118-IMAGE-UPLOAD-1): vision input,
    # current-turn only — history replay is a text fold and never carries them.
    # An image-only send (empty message) is valid; each image is validated by
    # ChatImage at the boundary, and the count is capped here.
    images: list[ChatImage] | None = Field(default=None, max_length=MAX_IMAGES_PER_MESSAGE)
    # OG118-TURN-SURVIVES-1: a client that can lose its socket without meaning
    # to (a phone leaving the foreground) asks the turn to finish anyway; the
    # answer lands in the record. Opt-in: a client that sets it must call
    # POST /chat/cancel on an explicit stop.
    survive_disconnect: bool = False


def _to_jsonable(value: object) -> object:
    """fi-runner events carry dataclasses (ToolCall, TurnResult). Convert them so
    the native shape survives as JSON; anything else falls back to str at dump."""
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return dataclasses.asdict(value)
    return value


# How long the turn may go quiet before the backend says "still alive". Well under
# the client's idle watchdog, so a healthy-but-slow turn re-arms it several times.
HEARTBEAT_INTERVAL_S = 15.0


async def _with_heartbeat(
    events: AsyncIterator[dict], interval: float = HEARTBEAT_INTERVAL_S
) -> AsyncIterator[dict]:
    """Yield the turn's events, injecting a `ping` whenever it goes quiet.

    A client's idle watchdog cannot tell "thinking" from "hung": both are silence.
    And silence is NORMAL here — an external element answers in ONE shot after up
    to 95s (external_engine._TIMEOUT), and a local turn can think far longer than
    a token gap. og118 shipped with no sign of life at all, so the browser killed
    healthy turns at 60s, DISCARDED what the user had written, and showed "la
    respuesta tardó demasiado" while the backend was still working. The ping
    carries nothing; its arrival is the whole point.
    """
    queue: asyncio.Queue = asyncio.Queue()
    done = object()

    async def pump() -> None:
        try:
            async for event in events:
                await queue.put(event)
        except Exception as exc:  # surface as a stream event, never a dead generator
            await queue.put({"type": "error", "message": str(exc)})
        finally:
            await queue.put(done)

    pump_task = asyncio.create_task(pump())
    try:
        while True:
            try:
                item = await asyncio.wait_for(queue.get(), timeout=interval)
            except asyncio.TimeoutError:
                yield {"type": "ping"}
                continue
            if item is done:
                return
            yield item
    finally:
        pump_task.cancel()


def _late_delivery(owner: str, conversation_id: str, user_text: str) -> Callable[[dict], Awaitable[None]]:
    """OG118-EXTERNAL-TURN-1: the external engine's answer outlived the live turn.
    It lands in the record the way a background job's does (the user's message
    rides along, since an unsettled turn is never persisted by the client), and
    the client's 15s conversation sync paints it."""
    user_copy = {"role": "user", "content": user_text, "timestamp": utc_now_iso()}

    async def entregar(assistant_message: dict) -> None:
        deps.get_conversation_store().append_late_turn(owner, conversation_id, user_copy, assistant_message)
        await _announce(owner, conversation_id, assistant_message)

    return entregar


def _abandoned_delivery(owner: str, conversation_id: str, user_text: str) -> detached_turn.LateDelivery:
    """OG118-TURN-SURVIVES-1: the local runner finished a turn nobody was
    listening to. It lands in the record exactly like a late external answer."""
    user_copy = {"role": "user", "content": user_text, "timestamp": utc_now_iso()}

    async def entregar(events: list[dict]) -> None:
        settled = [{k: _to_jsonable(v) for k, v in e.items()} for e in events]
        message = late_message(settled)
        result = next((e["result"] for e in settled if e.get("type") == "result"), None) or {}
        if result.get("model"):
            message["model"] = result["model"]
        deps.get_conversation_store().append_late_turn(owner, conversation_id, user_copy, message)
        await _announce(owner, conversation_id, message)

    return entregar


class CancelRequest(BaseModel):
    session_id: str


def _sse(event: dict) -> str:
    payload = {k: _to_jsonable(v) for k, v in event.items()}
    return f"data: {json.dumps(payload, default=str)}\n\n"


@router.post("/chat/stream")
async def chat_stream(
    req: ChatRequest,
    principal: Principal = Depends(get_principal),
    registry: ProjectRegistry = Depends(get_project_registry),
    rag: RagStoreClient = Depends(get_rag_store),
    seleccionar_runner: RunnerSelector = Depends(get_runner_selector),
    x_og118_client: str | None = Header(default=None),
) -> StreamingResponse:
    # Which build is alive, seen from outside: a native app that stops opening
    # stops appearing here, and its last line names the build that died.
    logger.info("chat turn client=%s", (x_og118_client or "web")[:40])
    # Con Proyectos apagado, un `corpus_id` que llegue se IGNORA en vez de
    # rechazarse: un cliente viejo (una pestaña sin recargar, una app móvil sin
    # actualizar) sigue chateando, sólo que sin corpus. Rechazarlo con 422 le
    # rompería el chat entero por una feature que él no pidió.
    corpus_id = req.corpus_id if proyectos_activos() else None

    # If a corpus is bound this turn, the caller must OWN it — turns corpus_id
    # from client-asserted into server-validated (no cross-account corpus reads).
    # Skipped for the legacy single shared account (bearer mode): there is one
    # tenant, ownership is moot, and pre-registry corpora keep working.
    if corpus_id and not principal.is_legacy_bearer and not registry.owns(corpus_id, principal.sub):
        raise HTTPException(status_code=404, detail="project not found")

    runner, element = seleccionar_runner(req.element)
    external = element is not None and element.engine_binding is not None and element.engine_binding.is_external

    async def generate() -> AsyncIterator[str]:
        # OG118-LIVING-CLAUDE (casita-per-chat): la casita AIRE de ESTE turno,
        # derivada del conversation_id del cliente. Se setea aquí adentro —
        # este frame es el contexto donde corre el pump del heartbeat, así que
        # AIREBackend.project_for_turn la ve; en la ruta claude-code nadie la
        # lee. Sin conversación → None → la casita fija de _backend_aire.
        AIRE_CHAT_PROJECT.set(aire_project_for_chat(req.session_id))
        request_id = uuid.uuid4().hex[:12]
        yield _sse({"type": "open", "request_id": request_id})
        # Announce WHO answers BEFORE the first token, so the client attributes
        # the bubble from its first character (fi-glass folds it into
        # ChatMessage.author). The parts ride alongside the composed label: the
        # UI needs the name and the symbol separately, and re-parsing
        # "53 · I · Yodo" client-side would be a contract nobody declared.
        # Absent when no element is selected — the base og118 persona answers,
        # and the shell attributes the turn to its own default author.
        if element is not None:
            yield _sse(
                {
                    "type": "element",
                    "element": {
                        "id": element.id,
                        "label": element.display_label,
                        "name": element.display_name,
                        "symbol": element.symbol,
                        "engine": element.engine_label,
                    },
                }
            )
        # ENGINE-BINDING-ADR-1: an external element runs on its own live engine, not
        # og118's runner. The turn rides the engine's ticket: its tool_call frames
        # stream live, its text lands whole. og118's session_id keys the engine's context.
        history = [m.model_dump() for m in req.history] if req.history else None
        if external:
            assert element is not None and element.engine_binding is not None
            # OG118-EXTERNAL-CORPUS-GAP-1 ruta 2: the external engine has no
            # rag_store tools, so the server retrieves the active project's
            # chunks HERE and folds them into the outbound text — the element
            # sees the user's documents without the remote engine knowing og118.
            # A retrieval failure refuses LOUD; answering without the documents
            # the user believes are in play is the silent lie this kills.
            outbound_text = req.message
            if corpus_id:
                try:
                    hits = await rag.search(corpus_id, req.message, top_k=4)
                except Exception:
                    yield _sse(
                        {
                            "type": "error",
                            "message": (
                                f"No pude consultar los documentos de tu proyecto para "
                                f"{element.display_name}. Reintenta, o quita el proyecto activo."
                            ),
                        }
                    )
                    yield _sse({"type": "done"})
                    return
                if hits:
                    context_block = "\n\n".join(h["text"] for h in hits)
                    outbound_text = (
                        "Contexto de los documentos del proyecto del usuario "
                        "(recuperado por el sistema — fundamenta tu respuesta en él):\n"
                        f"{context_block}\n---\n{req.message}"
                    )
            # The external-engine proxy is a text contract — it has no channel
            # for image blocks. Refuse LOUD (an in-stream error the shell shows)
            # instead of silently answering without the picture.
            if req.images:
                yield _sse(
                    {
                        "type": "error",
                        "message": (
                            f"El elemento {element.display_name} corre en un motor externo "
                            "y todavía no acepta imágenes. Quita la imagen o cambia de elemento."
                        ),
                    }
                )
                yield _sse({"type": "done"})
                return
            user_id = None if principal.is_legacy_bearer else principal.sub
            # The ticket proxy: the engine's tool_call frames arrive live from its event
            # log; the heartbeat covers the silences so the browser's 60s watchdog holds.
            entregar_tarde = (
                _late_delivery(principal.sub, req.session_id, req.message) if user_id and req.session_id else None
            )
            turno_externo = stream_external_turn(
                persona_id=element.engine_binding.persona_id,
                user_text=outbound_text,
                session_uuid=req.session_id,
                user_id=user_id,
                history=history,
                deliver_late=entregar_tarde,
            )
            if req.survive_disconnect and user_id and req.session_id:
                turno_externo = detached_turn.surviving(
                    turno_externo,
                    key=(principal.sub, req.session_id),
                    deliver_late=_abandoned_delivery(principal.sub, req.session_id, req.message),
                )
            async for ev in _with_heartbeat(turno_externo):
                yield _sse(ev)
            yield _sse({"type": "done"})
            return
        try:
            context = turn_context(corpus_id, registry)
            images = [i.model_dump() for i in req.images] if req.images else None
            # OG118-BACKGROUND-1: el MCP remoto de ESTE turno lleva en su URL la
            # cápsula firmada con la identidad, así que la tool sabe a quién entregar.
            remotos = background_tool_spec(principal.sub, req.session_id, corpus_id)
            runner_turno = (
                dataclasses.replace(runner, extra_mcp_servers=[*runner.extra_mcp_servers, *remotos])
                if remotos
                else runner
            )
            eventos = runner_turno.run_stream(
                req.message,
                session_id=req.session_id,
                request_id=request_id,
                history=history,
                context=context,
                images=images,
            )
            if req.survive_disconnect and req.session_id and not principal.is_legacy_bearer:
                eventos = detached_turn.surviving(
                    eventos,
                    key=(principal.sub, req.session_id),
                    deliver_late=_abandoned_delivery(principal.sub, req.session_id, req.message),
                )
            async for event in _with_heartbeat(eventos):
                yield _sse(event)
        except Exception as exc:  # surface as a stream event, never a 500 mid-stream
            yield _sse({"type": "error", "message": str(exc)})
        yield _sse({"type": "done"})

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/chat/cancel")
async def chat_cancel(req: CancelRequest, principal: Principal = Depends(get_principal)) -> dict:
    """The explicit stop of a turn that would otherwise outlive its connection."""
    return {"cancelled": detached_turn.cancel((principal.sub, req.session_id))}
