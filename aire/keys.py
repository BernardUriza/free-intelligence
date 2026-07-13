"""Nombres legibles afuera, UUIDs adentro. Sin tabla de mapeo.

El SDK exige que `session_id` sea UUID y lo valida, pero deja fijarlo. Derivarlo
determinísticamente del nombre (`uuid5`) es lo que hace innecesaria una tabla de
mapeo: el mismo nombre siempre resuelve a la misma sesión, incluso tras un
reinicio — que es el punto entero de la memoria.
"""

from __future__ import annotations

import uuid

AIRE_NAMESPACE = uuid.UUID("a13e0000-0000-4000-8000-000000000000")


def sdk_session_uuid(session: str) -> str:
    """El nombre externo de la sesión → el UUID que el SDK demanda."""
    return str(uuid.uuid5(AIRE_NAMESPACE, session))
