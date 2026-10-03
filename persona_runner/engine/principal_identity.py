"""Identidad por superficie → principal canónico (F2 del checklist, 2026-09-27).

La memoria longitudinal está keyed por el id con el que cada superficie conoce
a la persona: Discord la nombra por snowflake (`907264175246569543`), og118 por
el `sub` de Auth0 (`auth0|…`, `google-oauth2|…`). Sin un puente, el mismo humano
es DOS principales y el agente web arranca amnésico frente a 8,707 facts que sí
existen bajo el snowflake.

El puente es una tabla explícita: `(surface, external_id) → principal_id`. Se
llena a mano (`scripts/link_identity.py`), nunca por inferencia — ligar cuentas
adivinando es la clase de bug del sangrado cross-principal. Un id sin fila pasa
tal cual (hoy el id ES el principal, y así sigue funcionando Discord); si además
no parece un snowflake, se loguea `principal_identity_unlinked` para que la
primera visita desde una superficie nueva deje su `sub` en KQL en vez de perderse.

Mismo patrón que `aire_principal`: el módulo posee su DDL y lo aplica una vez
por proceso sobre el pool compartido de `mcp_tools.shared`. Cualquier fallo de
Postgres degrada a "sin puente": un turno sin memoria vale más que un turno
muerto (ley del repo).
"""

from __future__ import annotations

import re

import structlog

from persona_runner.core.schemas import TurnRequest
from persona_runner.mcp_tools import shared

log = structlog.get_logger()

_DDL = """
CREATE TABLE IF NOT EXISTS principal_identities (
    surface      TEXT NOT NULL,
    external_id  TEXT NOT NULL,
    principal_id TEXT NOT NULL,
    linked_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    linked_by    TEXT,
    PRIMARY KEY (surface, external_id)
);
CREATE INDEX IF NOT EXISTS idx_principal_identities_principal
    ON principal_identities (principal_id)
"""

# Un snowflake de Discord: 15 a 22 dígitos. Es el único formato que hoy ES un
# principal por sí mismo; cualquier otro id sin fila es una identidad sin ligar.
_SNOWFLAKE = re.compile(r"^\d{15,22}$")

_ddl_applied = False


async def _ensure_ddl(conn) -> None:
    global _ddl_applied
    if not _ddl_applied:
        await conn.execute(_DDL)
        _ddl_applied = True


def looks_like_snowflake(external_id: str) -> bool:
    return bool(_SNOWFLAKE.match(external_id))


async def resolve(external_id: str, surface: str | None) -> str:
    """El principal canónico detrás de `external_id`, o el mismo id si no hay puente.

    Con `surface` la búsqueda es exacta. Sin ella (clientes que aún no lo mandan)
    se busca el id en todas las superficies y sólo se acepta un match ÚNICO: dos
    superficies distintas con el mismo id externo es una colisión, no una
    identidad, y se deja pasar sin resolver."""
    try:
        async with shared.acquire() as conn:
            if conn is None:
                return external_id
            await _ensure_ddl(conn)
            if surface:
                rows = await conn.fetch(
                    "SELECT surface, principal_id FROM principal_identities WHERE surface = $1 AND external_id = $2",
                    surface,
                    external_id,
                )
            else:
                rows = await conn.fetch(
                    "SELECT surface, principal_id FROM principal_identities WHERE external_id = $1",
                    external_id,
                )
    except Exception:
        log.exception("principal_identity_lookup_failed", surface=surface, external_id=external_id)
        return external_id

    if len(rows) == 1:
        principal_id = rows[0]["principal_id"]
        log.info(
            "principal_identity_resolved",
            surface=rows[0]["surface"],
            external_id=external_id,
            principal_id=principal_id,
        )
        return principal_id
    if len(rows) > 1:
        log.warning(
            "principal_identity_ambiguous",
            external_id=external_id,
            surfaces=sorted(r["surface"] for r in rows),
        )
        return external_id
    if not looks_like_snowflake(external_id):
        log.warning("principal_identity_unlinked", surface=surface, external_id=external_id)
    return external_id


async def apply(req: TurnRequest) -> TurnRequest:
    """El request con `user_id` ya canónico. Se llama en la puerta del runner,
    ANTES de `fetch_user_facts` y del bind del principal MCP, para que todo lo
    que lee memoria por `user_id` vea al mismo humano."""
    principal_id = await resolve(req.user_id, req.surface)
    if principal_id == req.user_id:
        return req
    return req.model_copy(update={"user_id": principal_id})
