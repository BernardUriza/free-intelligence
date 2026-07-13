"""AIRE es dueño del SDK.

Este archivo es una COPIA del motor de `ClaudeCodeBackend` de fi-runner —el que
ya poseía el Claude Agent SDK: arranca el `ClaudeSDKClient`, corre el turn loop,
drena los eventos tipados— despojado de toda dependencia a fi-runner, y con las
dos cosas que hacen a AIRE lo que es:

- **MODOS.** `complete` (sin herramientas — el SUSTITUTO de la Messages API cruda)
  y `agent` (con herramientas — el MEJORADOR: una sesión de Claude Code que ejecuta
  tools). El SDK es el motor de UN modo, no la identidad de AIRE.
- **MEMORIA propia.** El `session_store` de Postgres, dueño único, inyectado. La
  Claude API es stateless; AIRE es "la Claude API pero que se acuerda".

Lo que NO se hace: importar fi-runner. AIRE posee este código. Ésa es toda la
diferencia con la versión que estuvo mal — antes AIRE *importaba* el motor y
dependía de un repo que otro agente editaba; ahora lo posee.
"""

from __future__ import annotations

import asyncio
import os
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from claude_agent_sdk import ClaudeSDKClient, project_key_for_directory

from .keys import sdk_session_uuid

WORKSPACES = Path(__file__).resolve().parent.parent / "workspaces"

SYSTEM_PROMPT = (
    "Eres un agente que trabaja dentro de AIRE. Tu trabajo aparece, en vivo, en "
    "una página HTML que el servidor va escribiendo conforme piensas. Usa tus "
    "herramientas cuando te sirvan: cada llamada se pinta en la página."
)

# Los modos: el dial que hace a AIRE sustituto Y mejorador.
#   complete → sin herramientas, sin loop agéntico → el sustituto de la API cruda.
#   agent    → herramientas + BYPASS → el mejorador que ejecuta tools.
# OJO con BYPASS: concede TODAS las builtins EXCEPTO las de `disallowed` — la
# allowlist es decorativa bajo ese modo, lo que de verdad contiene es `disallowed`.
# `Bash` queda fuera; el confinamiento real del filesystem es `SandboxSettings`,
# aún no puesto — `cwd` NO es una jaula.
MODES: dict[str, dict[str, Any]] = {
    "complete": {
        "allowed_tools": [],
        "disallowed_tools": ["Bash", "Read", "Write", "Edit", "Glob", "Grep", "WebSearch", "WebFetch"],
        "permission_mode": "default",
    },
    "agent": {
        "allowed_tools": ["Read", "Write", "Glob", "Grep", "WebSearch", "WebFetch"],
        "disallowed_tools": ["Bash"],
        "permission_mode": "bypassPermissions",
    },
}
DEFAULT_MODE = "agent"


@dataclass(frozen=True)
class ToolCall:
    """Una llamada a herramienta, tal como se pinta en la página. Copiada del
    contrato de fi-runner, mínima: solo lo que la interfaz necesita mostrar."""

    name: str
    input: dict[str, Any] | None = None
    id: str | None = None
    is_error: bool | None = None
    duration_ms: int | None = None


@dataclass(frozen=True)
class TurnResult:
    text: str
    usage: dict[str, Any] | None = None
    session_id: str | None = None
    tool_calls: tuple[ToolCall, ...] = ()


class Engine:
    """El motor de AIRE: dueño del SDK, de los modos y de la memoria.

    Un cliente `ClaudeSDKClient` vivo por sesión (pool = caché caliente). Un miss
    no significa que la sesión murió: se reconstruye desde el store con `resume=`,
    que es lo que vuelve a la memoria sobreviviente al reinicio del proceso.
    """

    def __init__(self, session_store: Any) -> None:
        self.session_store = session_store
        self._pool: dict[str, ClaudeSDKClient] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._pool_lock = asyncio.Lock()

    def _cwd(self, project: str) -> Path:
        ws = WORKSPACES / project
        ws.mkdir(parents=True, exist_ok=True)
        return ws

    def session_key(self, project: str, session: str) -> dict[str, str]:
        """La llave del store. El `project_key` NO se inventa: el SDK lo deriva del
        `cwd` (`project_key_for_directory`) cuando ESCRIBE el transcript, así que el
        lado que LEE debe derivarlo igual o cada `load()` falla."""
        return {
            "project_key": project_key_for_directory(str(self._cwd(project))),
            "session_id": sdk_session_uuid(session),
        }

    async def has_session(self, project: str, session: str) -> bool:
        return bool(await self.session_store.load(self.session_key(project, session)))

    def _build_options(self, project: str, session: str, mode: str, resuming: bool) -> Any:
        from claude_agent_sdk import ClaudeAgentOptions

        policy = MODES.get(mode, MODES[DEFAULT_MODE])
        sdk_uuid = sdk_session_uuid(session)
        env = {"CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1"}
        if os.environ.get("AIRE_ISOLATE_CONFIG") == "1":
            # En contenedor: sin Keychain, la credencial entra por env y
            # CLAUDE_CONFIG_DIR=/tmp hace que el contenedor no guarde nada. En local
            # NO se fuerza (la credencial viva del CLI vive en el Keychain de macOS).
            cfg = Path("/tmp/aire-config") / project
            cfg.mkdir(parents=True, exist_ok=True)
            env["CLAUDE_CONFIG_DIR"] = str(cfg)
        kwargs: dict[str, Any] = {
            "system_prompt": SYSTEM_PROMPT,
            "allowed_tools": list(policy["allowed_tools"]),
            "disallowed_tools": list(policy["disallowed_tools"]),
            "permission_mode": policy["permission_mode"],
            "cwd": str(self._cwd(project)),
            "setting_sources": [],  # NO heredar el CLAUDE.md/settings de la máquina
            "strict_mcp_config": True,  # NO heredar los MCP de la máquina anfitriona
            "env": env,
            "session_store": self.session_store,
            "session_store_flush": "eager",  # sin ventana de pérdida si el proceso muere
        }
        # session_id=<uuid> PONE el id de una sesión que NACE; resume=<uuid>
        # RECUPERA una existente. Son mutuamente excluyentes: pasar session_id en una
        # continuación NO resume, arranca una nueva pisando el id y perdiendo la
        # memoria. Por eso preguntamos al store (has_session), no adivinamos del pool.
        if resuming:
            kwargs["resume"] = sdk_uuid
        else:
            kwargs["session_id"] = sdk_uuid
        return ClaudeAgentOptions(**kwargs)

    async def _client_for(self, project: str, session: str, mode: str) -> tuple[ClaudeSDKClient, asyncio.Lock]:
        pool_key = f"{project}/{session}"
        async with self._pool_lock:
            client = self._pool.get(pool_key)
            if client is None:
                resuming = await self.has_session(project, session)
                options = self._build_options(project, session, mode, resuming)
                client = ClaudeSDKClient(options=options)
                await client.__aenter__()
                self._pool[pool_key] = client
            lock = self._locks.setdefault(pool_key, asyncio.Lock())
        return client, lock

    async def run_stream(
        self, project: str, session: str, prompt: str, mode: str = DEFAULT_MODE
    ) -> AsyncIterator[dict[str, Any]]:
        """Un turno, en vivo. Emite {"type": "text"|"tool_call"|"result", ...} según
        ocurre. El transcript se refleja a Postgres solo (session_store) — la memoria
        del agente Y la memoria de la página son EL MISMO transcript."""
        client, lock = await self._client_for(project, session, mode)
        async with lock:  # serializa turnos en el mismo cliente (no es concurrency-safe)
            await client.query(prompt)
            async for event in self._drain(client):
                yield event

    @staticmethod
    async def _drain(client: ClaudeSDKClient) -> AsyncIterator[dict[str, Any]]:
        """Drena la respuesta del SDK y la emite en vivo. Copiado del turn loop
        probado de fi-runner: los tipos se identifican por `type(m).__name__`
        (defensivo entre versiones del SDK), y el RESULTADO de una herramienta no
        vuelve como mensaje del asistente sino como `ToolResultBlock` en un mensaje
        de USUARIO — se emparejan por `tool_use_id`."""
        parts: list[str] = []
        usage: dict[str, Any] | None = None
        session_id: str | None = None
        tools: list[ToolCall] = []
        by_id: dict[str, int] = {}
        start_ts: dict[str, float] = {}
        async for message in client.receive_response():
            kind = type(message).__name__
            content = getattr(message, "content", None)
            if kind == "AssistantMessage" and isinstance(content, list):
                for block in content:
                    btype = type(block).__name__
                    if btype == "TextBlock":
                        text = getattr(block, "text", "") or ""
                        if text:
                            parts.append(text)
                            yield {"type": "text", "text": text}
                    elif btype == "ToolUseBlock":
                        tc = ToolCall(
                            name=getattr(block, "name", "") or "",
                            input=getattr(block, "input", None),
                            id=getattr(block, "id", None),
                        )
                        if tc.id is not None:
                            by_id[tc.id] = len(tools)
                            start_ts[tc.id] = time.monotonic()
                        tools.append(tc)
                        yield {"type": "tool_call", "tool": tc}
            elif kind == "UserMessage" and isinstance(content, list):
                for block in content:
                    if type(block).__name__ != "ToolResultBlock":
                        continue
                    use_id = getattr(block, "tool_use_id", None)
                    idx = by_id.get(use_id)
                    if idx is not None:
                        raw_err = getattr(block, "is_error", None)
                        t0 = start_ts.get(use_id)
                        dur = int((time.monotonic() - t0) * 1000) if t0 is not None else None
                        tools[idx] = replace(
                            tools[idx],
                            is_error=None if raw_err is None else bool(raw_err),
                            duration_ms=dur,
                        )
            elif kind == "ResultMessage":
                raw = getattr(message, "usage", None)
                if raw is not None:
                    usage = dict(raw) if isinstance(raw, dict) else dict(getattr(raw, "__dict__", {}) or {})
                    cost = getattr(message, "total_cost_usd", None)
                    if cost is not None:
                        usage["total_cost_usd"] = cost
                session_id = getattr(message, "session_id", None) or session_id
        yield {
            "type": "result",
            "result": TurnResult(text="".join(parts), usage=usage, session_id=session_id, tool_calls=tuple(tools)),
        }

    async def load_transcript(self, project: str, session: str) -> list[dict[str, Any]]:
        """Lo que el agente recuerda, que es lo mismo que la página vuelve a pintar.
        El transcript no vive en la conexión HTTP: vive en Postgres."""
        return await self.session_store.load(self.session_key(project, session)) or []

    async def aclose(self) -> None:
        async with self._pool_lock:
            for client in self._pool.values():
                try:
                    await client.__aexit__(None, None, None)
                except Exception:  # noqa: BLE001 - best-effort teardown
                    pass
            self._pool.clear()
            self._locks.clear()
