"""El principal DURABLE del turno en curso, por casita — la mitad remota del
binding de identidad.

En la ruta local la identidad viaja en un ContextVar (`mcp_tools/turn_context`):
el servidor la ata, el modelo jamás la pide. En la ruta AIRE las tools corren
como llamadas HTTP que el agente del droplet hace de vuelta a ESTE runner
(`api/mcp_http.py`), y esa request llega en otro proceso, otra réplica, otro
contexto — el ContextVar no la alcanza. Lo que sí la alcanza es Postgres.

El rail: `_run_turn` (bajo el lock de la casita) escribe la fila
(casita → user_id, channel_id) al abrir el turno y la borra al cerrarlo; el
endpoint MCP resuelve el principal por la casita que viene en su URL. Como los
turnos de una casita están serializados por el lock (y AIRE serializa por
sesión), la fila viva es siempre EL turno en curso. Sin fila no se adivina:
la tool contesta error — adivinar es exactamente el bug del 2026-08-10.

Mismo patrón que `aire_topic`: el módulo posee su DDL y lo aplica una vez por
proceso, sobre el pool compartido de `mcp_tools.shared`.
"""

from __future__ import annotations

from dataclasses import dataclass

import structlog

from persona_runner.mcp_tools import shared

log = structlog.get_logger()

_DDL = """
CREATE TABLE IF NOT EXISTS aire_turn_principals (
    casita      TEXT PRIMARY KEY,
    user_id     TEXT NOT NULL,
    channel_id  TEXT NOT NULL,
    agent_id    TEXT NOT NULL DEFAULT '',
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE aire_turn_principals ADD COLUMN IF NOT EXISTS agent_id TEXT NOT NULL DEFAULT ''
"""

_ddl_applied = False


@dataclass(frozen=True)
class RemotePrincipal:
    user_id: str
    channel_id: str
    agent_id: str = ""


async def _ensure_ddl(conn) -> None:
    global _ddl_applied
    if not _ddl_applied:
        await conn.execute(_DDL)
        _ddl_applied = True


async def bind(casita: str, *, user_id: str, channel_id: str, agent_id: str) -> bool:
    """Publica el principal del turno que ESTA casita está sirviendo ahora.
    Devuelve False (y loguea) si Postgres no está — el turno sigue; las tools
    remotas de ese turno contestarán que no hay principal, nunca un adivinado."""
    async with shared.acquire() as conn:
        if conn is None:
            log.warning("aire_principal_bind_skipped", casita=casita)
            return False
        await _ensure_ddl(conn)
        await conn.execute(
            "INSERT INTO aire_turn_principals (casita, user_id, channel_id, agent_id, updated_at) "
            "VALUES ($1, $2, $3, $4, now()) "
            "ON CONFLICT (casita) DO UPDATE SET user_id = $2, channel_id = $3, agent_id = $4, updated_at = now()",
            casita,
            user_id,
            channel_id,
            agent_id,
        )
        return True


async def clear(casita: str) -> None:
    """Cierra la ventana: sin turno en curso, ninguna tool remota resuelve identidad."""
    async with shared.acquire() as conn:
        if conn is None:
            return
        await _ensure_ddl(conn)
        await conn.execute("DELETE FROM aire_turn_principals WHERE casita = $1", casita)


async def lookup(casita: str) -> RemotePrincipal | None:
    async with shared.acquire() as conn:
        if conn is None:
            return None
        await _ensure_ddl(conn)
        row = await conn.fetchrow(
            "SELECT user_id, channel_id, agent_id FROM aire_turn_principals WHERE casita = $1", casita
        )
    if row is None:
        return None
    return RemotePrincipal(user_id=row["user_id"], channel_id=row["channel_id"], agent_id=row["agent_id"])
