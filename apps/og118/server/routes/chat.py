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
from runner import AIRE_CHAT_PROJECT, aire_project_for_chat, background_tool_spec, files_tool_spec

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


# Vision caps for a hostile or buggy client; the composer downscales, so a compliant one never hits them.
# Anthropic's limit is 5 MB decoded; base64 inflates 4/3, hence the string cap.
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
    # Client-supplied history, replayed each turn: continuity survives a replica recycle with no server-side store.
    history: list[HistoryMessage] | None = None
    # The active project's corpus for this turn; it scopes the agent's rag_store search.
    # Ownership is validated in the handler before the stream opens.
    corpus_id: str | None = None
    # A token the registry resolves (slug, symbol, atomic number or alias). An active element swaps the persona;
    # absent, unknown or inactive means the base og118 persona.
    element: str | None = None
    # Vision input for THIS turn only; history replay is a text fold and never carries images.
    # An image-only send (empty message) is valid.
    images: list[ChatImage] | None = Field(default=None, max_length=MAX_IMAGES_PER_MESSAGE)
    # A client that can lose its socket without meaning to asks the turn to finish anyway; the answer lands in the record.
    # Opt-in: such a client must call POST /chat/cancel on an explicit stop.
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
    # Con Proyectos apagado, un `corpus_id` que llegue se ignora en vez de rechazarse:
    # un cliente viejo sigue chateando sin corpus en lugar de recibir un 422.
    corpus_id = req.corpus_id if proyectos_activos() else None

    # A bound corpus must be OWNED by the caller: no cross-account corpus reads.
    # Skipped for the legacy shared bearer, where there is one tenant.
    if corpus_id and not principal.is_legacy_bearer and not registry.owns(corpus_id, principal.sub):
        raise HTTPException(status_code=404, detail="project not found")

    runner, element = seleccionar_runner(req.element)
    external = element is not None and element.engine_binding is not None and element.engine_binding.is_external

    async def generate() -> AsyncIterator[str]:
        # La casita AIRE de este turno sale del conversation_id. Se fija AQUÍ porque este frame es el contexto
        # donde corre el pump del heartbeat, y de ahí la lee AIREBackend.
        AIRE_CHAT_PROJECT.set(aire_project_for_chat(req.session_id))
        request_id = uuid.uuid4().hex[:12]
        yield _sse({"type": "open", "request_id": request_id})
        # Announce WHO answers before the first token, so the client attributes the bubble from its first character.
        # Name and symbol ride separately: re-parsing the composed label client-side would be an undeclared contract.
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
        # An external element runs on its own engine: its tool_call frames stream live and its text lands whole.
        # og118's session_id keys the engine's context.
        history = [m.model_dump() for m in req.history] if req.history else None
        if external:
            assert element is not None and element.engine_binding is not None
            # The external engine has no rag_store tools, so the server retrieves the project's chunks here and folds them in.
            # A retrieval failure refuses loud: answering without the documents the user believes are in play would be a lie.
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
            # The external-engine proxy is a text contract with no channel for images:
            # refuse in-stream instead of answering without the picture.
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
            remotos = [
                *background_tool_spec(principal.sub, req.session_id, corpus_id),
                *files_tool_spec(principal.sub, req.session_id),
            ]
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
