"""Un `project` / `session` viene de la URL: entrada hostil hasta probar lo
contrario. Se usa para construir un path de filesystem (`workspaces/<project>`) y
una llave de Postgres, así que un `..` o una barra lo sacan de su jaula. La
defensa no es sanitizar (quitar los `..` y rezar): es un ALLOWLIST estrecho. Lo
que no cabe, se rechaza — no se "arregla".
"""

from __future__ import annotations

import re

_VALID = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")


class InvalidName(ValueError):
    """El project/session no pasó el allowlist."""


def clean(kind: str, value: str) -> str:
    if not _VALID.match(value or ""):
        raise InvalidName(f"{kind} inválido: {value!r} (permitido: letras, números, - y _, 1–64)")
    return value
