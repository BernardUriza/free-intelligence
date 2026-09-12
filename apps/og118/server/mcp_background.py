"""La puerta MCP-sobre-HTTP de `start_background_task` — para el agente que corre en AIRE.

Clon del patrón de discord-bot (`persona_runner/api/mcp_http.py`): la tool vive
AQUÍ, donde están el share de jobs y la identidad que arranca el worker, y el
agente remoto la llama por HTTPS. AIRE sólo cablea la URL (`remote_tools`, con
el origen de este servidor en su allowlist).

- **Stateless a propósito.** Cada POST es un JSON-RPC completo; no se emite
  MCP-Session-Id.
- **La identidad no viene del modelo: viene de la cápsula firmada en la URL**,
  que este runner armó al abrir el turno (`background_tool_spec`). Vencida o
  mal firmada → la tool contesta error, jamás adivina.
- **El bearer es de este runner para este runner** (`OG118_MCP_TOKEN`). Sin token
  en el env, la puerta entera es 404 — apagada, no abierta.
"""

from __future__ import annotations

import hmac
import json
import logging
import os
from typing import Any

from fastapi import APIRouter, Request, Response

import background_jobs
from background_jobs import JobStore, Starter, verify_capsule

log = logging.getLogger("og118.background")
router = APIRouter()

PROTOCOL_VERSION = "2025-06-18"
SERVER_NAME = "background"
TOOL_NAME = "start_background_task"

_job_store: JobStore | None = None
_starter: Starter = background_jobs.start_execution


def get_job_store() -> JobStore:
    """Un JSON por job junto a las conversaciones, en el share. Overridable en tests."""
    global _job_store
    if _job_store is None:
        default = os.path.join(
            os.path.dirname(os.getenv("FI_RAG_STORE_PATH", "/opt/fi/data/fi_rag_store.h5")), "jobs"
        )
        _job_store = JobStore(os.getenv("OG118_JOBS_PATH", default))
    return _job_store


def _token() -> str:
    return os.environ.get("OG118_MCP_TOKEN", "").strip()


def _authorized(request: Request) -> bool:
    expected = _token()
    got = request.headers.get("authorization", "")
    return bool(expected) and hmac.compare_digest(got, f"Bearer {expected}")


def _rpc_result(id_: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": id_, "result": result}


def _rpc_error(id_: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": id_, "error": {"code": code, "message": message}}


def _tools_list() -> dict[str, Any]:
    return {
        "tools": [
            {
                "name": TOOL_NAME,
                "description": (
                    "Queue a task to be finished AFTER this reply by a background worker that has "
                    "this conversation as context. Its result arrives as a new assistant message in "
                    "this same conversation. Give a complete, self-contained goal."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "goal": {"type": "string", "description": "What the worker must do and deliver, fully specified."}
                    },
                    "required": ["goal"],
                },
            }
        ]
    }


def _text(text: str, *, error: bool = False) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": text}], "isError": error}


def _tools_call(capsule: str, params: dict[str, Any]) -> dict[str, Any]:
    if params.get("name") != TOOL_NAME:
        return _text(f"unknown tool {params.get('name')!r}", error=True)
    identidad = verify_capsule(_token(), capsule)
    if identidad is None:
        return _text("this turn's background window is closed — do the work now, in this reply", error=True)
    goal = str((params.get("arguments") or {}).get("goal") or "").strip()
    if not goal:
        return _text("goal is required", error=True)
    resource = os.environ.get("OG118_JOB_RESOURCE_ID", "").strip()
    if not resource:
        return _text("background execution is not configured on this deployment", error=True)
    store = get_job_store()
    job = store.create(owner=identidad["sub"], conversation_id=identidad["cid"], goal=goal,
                       corpus_id=identidad.get("corpus"))
    try:
        execution = _starter(resource)
    except Exception as exc:
        store.fail(store.claim_next() or job, f"start failed: {exc}")
        log.exception("background_start_failed", extra={"job": job["id"]})
        return _text("the background worker could not be started — do the work now, in this reply", error=True)
    log.info("background_job_queued job=%s execution=%s", job["id"], execution)
    return _text(
        f"Queued as background job {job['id']}. The result will arrive as a new message in this "
        "conversation; tell the user that, without a time estimate."
    )


@router.post("/mcp/background/{capsule}")
async def mcp_endpoint(capsule: str, request: Request) -> Response:
    if not _authorized(request):
        return Response(status_code=404)
    body = await request.json()
    method, id_ = body.get("method"), body.get("id")
    if id_ is None:
        return Response(status_code=202)
    if method == "initialize":
        result: dict[str, Any] = {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": SERVER_NAME, "version": "1.0.0"},
        }
    elif method == "tools/list":
        result = _tools_list()
    elif method == "tools/call":
        result = _tools_call(capsule, dict(body.get("params") or {}))
    elif method == "ping":
        result = {}
    else:
        return _json(_rpc_error(id_, -32601, f"method {method!r} not supported"))
    return _json(_rpc_result(id_, result))


def _json(payload: dict[str, Any]) -> Response:
    return Response(content=json.dumps(payload), media_type="application/json")
