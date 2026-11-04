"""Quién es el usuario de ESTE turno — atado por el servidor, nunca pedido al modelo.

Las tools de memoria recibían `user_id` como parámetro, o sea que la identidad
sobre la que operaban venía escrita por el modelo. Eso es el patrón que OWASP
LLM06 llama excessive agency y la literatura llama *confused deputy*: un gate de
capacidades dice QUÉ puede llamarse, jamás SOBRE QUIÉN. El 2026-08-10 una persona
le atribuyó a Bernard un fact de Alex — "el THC que te falló cuando murió tu
madre", cuando la madre de Bernard está viva y es fiadora de su loft; la que
falleció es la de Alex. Los dos son snowflakes válidos, así que ninguna
validación de formato lo habría detenido.

La cura no es validar mejor el parámetro: es que el parámetro no exista.

Un ContextVar y no un valor fijo al construir la sesión, porque el pool se llavea
por `channel_id[:persona_id]` (hoy la casita `{persona}-{canal}`) y un canal es
multi-usuario — en #general la misma sesión atiende a Bernard y a Alex. Atar al
crear la sesión congelaría al primero que habló. El principal cambia turno a
turno; el binding tiene que cambiar con él.

`contextvars` es seguro con asyncio: cada tarea hereda una copia del contexto, y
un `set` dentro de un turno no se ve desde otro que corra en paralelo en el mismo
event loop.
"""

from __future__ import annotations

import contextvars
from dataclasses import dataclass


@dataclass(frozen=True)
class TurnPrincipal:
    """El usuario, el canal y la persona de un turno concreto.

    `agent_id` es la persona que está hablando (el stem de su ADN, igual a
    `agents.name`): la dueña de los `agent_facts` que este turno puede tocar. Vacío
    cuando el camino que ató el turno no conoce a la persona — y entonces las tools
    de autoconocimiento se niegan en vez de dejar que el modelo la nombre.
    """

    user_id: str
    channel_id: str
    agent_id: str = ""


_CURRENT: contextvars.ContextVar[TurnPrincipal | None] = contextvars.ContextVar(
    "persona_runner_turn_principal", default=None
)


class NoTurnPrincipalError(RuntimeError):
    """Una tool de memoria corrió fuera de un turno con principal atado.

    Es un error del servidor, no del modelo: significa que alguien añadió un
    camino de invocación que no pasa por `bind_turn_principal`. Se cae fuerte en
    vez de adivinar un usuario, porque adivinar es exactamente el bug original.
    """


def bind_turn_principal(*, user_id: str, channel_id: str, agent_id: str = "") -> contextvars.Token:
    """Ata el principal del turno. Lo llama el handler del turno, nadie más."""
    return _CURRENT.set(TurnPrincipal(user_id=user_id, channel_id=channel_id, agent_id=agent_id))


def reset_turn_principal(token: contextvars.Token) -> None:
    _CURRENT.reset(token)


def current_principal() -> TurnPrincipal:
    """El principal del turno en curso, o revienta."""
    principal = _CURRENT.get()
    if principal is None:
        raise NoTurnPrincipalError(
            "una tool de memoria corrió sin principal atado: el turno no pasó por "
            "bind_turn_principal, así que no hay forma honesta de saber de quién "
            "son los datos que se están pidiendo"
        )
    return principal
