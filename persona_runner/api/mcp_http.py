"""La puerta MCP-sobre-HTTP de las tools de memoria — para el agente que corre en AIRE.

La etapa 2 dejó a la persona con 2 de sus 10 tools de memoria: las in-process no
viajan al droplet, y el droplet no puede tocar el Postgres de Khimeras (no tiene
— ni tendrá — su credencial). Este endpoint cierra el hueco al revés: las tools
se quedan AQUÍ, donde viven las credenciales, y el agente remoto las llama por
HTTPS. AIRE sólo cablea la URL (`remote_tools`, aire-server #48, con el origen
de este runner en su allowlist); el SDK del droplet habla MCP streamable HTTP.

Tres decisiones que cargan peso:

- **Stateless a propósito.** Cada POST es un JSON-RPC completo (initialize /
  tools/list / tools/call); no se emite MCP-Session-Id. Sin estado no hay
  réplica equivocada ni sesión que expirar.
- **La identidad no viene del modelo NI del droplet: viene de la fila durable**
  que `aire_route` publica bajo el lock de la casita (`engine/aire_principal`).
  La casita llega en la URL — la parte del path la eligió este runner al armar
  el spec, no el agente. Sin fila viva → la tool contesta error, jamás adivina.
- **El bearer es de este runner para este runner** (`RUNNER_MCP_TOKEN`): viaja
  en el spec que mandamos a AIRE y vuelve en cada llamada. Sin token en el env,
  la puerta entera es 404 — apagada, no abierta.

Las tools son EXACTAMENTE las de `mcp_tools/` (mismos objetos SdkMcpTool, mismo
ContextVar de principal) — cero forks de lógica entre la ruta local y la remota.
"""

from __future__ import annotations

import hmac
import os
from typing import Any

import structlog
from fastapi import APIRouter, Request, Response

from persona_runner.engine import aire_principal
from persona_runner.mcp_tools import PERSONA_MEMORY_TOOLS
from persona_runner.mcp_tools.turn_context import bind_turn_principal, reset_turn_principal

log = structlog.get_logger()
router = APIRouter()

PROTOCOL_VERSION = "2025-06-18"
_TOOLS = {t.name: t for t in PERSONA_MEMORY_TOOLS}


def _token() -> str:
    return os.environ.get("RUNNER_MCP_TOKEN", "").strip()


def _authorized(request: Request) -> bool:
    expected = _token()
    got = request.headers.get("authorization", "")
    return bool(expected) and hmac.compare_digest(got, f"Bearer {expected}")


def _rpc_result(id_: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": id_, "result": result}


def _rpc_error(id_: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": id_, "error": {"code": code, "message": message}}


def _tools_list() -> dict[str, Any]:
    from claude_agent_sdk import _build_input_schema  # the SDK's own converter,

    # the same one create_sdk_mcp_server feeds the in-process transport — one
    # schema source for both routes, not a hand-copied second truth.
    return {
        "tools": [
            {"name": t.name, "description": t.description, "inputSchema": _build_input_schema(t)}
            for t in _TOOLS.values()
        ]
    }


async def _tools_call(casita: str, params: dict[str, Any]) -> dict[str, Any]:
    tool = _TOOLS.get(str(params.get("name")))
    if tool is None:
        return {"content": [{"type": "text", "text": f"unknown tool {params.get('name')!r}"}], "isError": True}
    principal = await aire_principal.lookup(casita)
    if principal is None:
        return {
            "content": [{"type": "text", "text": "no live turn principal for this casita — the turn window is closed"}],
            "isError": True,
        }
    token = bind_turn_principal(user_id=principal.user_id, channel_id=principal.channel_id)
    try:
        out = await tool.handler(dict(params.get("arguments") or {}))
    except Exception:
        log.exception("mcp_http_tool_failed", casita=casita, tool=tool.name)
        return {"content": [{"type": "text", "text": f"{tool.name} failed server-side"}], "isError": True}
    finally:
        reset_turn_principal(token)
    return {"content": out.get("content", []), "isError": bool(out.get("is_error"))}


@router.post("/mcp/{casita}")
async def mcp_endpoint(casita: str, request: Request) -> Response:
    if not _authorized(request):
        # 404 on purpose: an unauthenticated caller learns nothing about the
        # surface, and an unset token means the whole door does not exist.
        return Response(status_code=404)
    body = await request.json()
    method, id_ = body.get("method"), body.get("id")
    if id_ is None:  # a notification (e.g. notifications/initialized) — ack, no body
        return Response(status_code=202)
    if method == "initialize":
        result = {
            "protocolVersion": PROTOCOL_VERSION,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "persona_memory", "version": "2.0.0"},
        }
    elif method == "tools/list":
        result = _tools_list()
    elif method == "tools/call":
        result = await _tools_call(casita, dict(body.get("params") or {}))
    elif method == "ping":
        result = {}
    else:
        return _json(_rpc_error(id_, -32601, f"method {method!r} not supported"))
    return _json(_rpc_result(id_, result))


def _json(payload: dict[str, Any]) -> Response:
    import json

    return Response(content=json.dumps(payload), media_type="application/json")
