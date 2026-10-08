"""La puerta de recepción del gateway — cerrarla es lo que hace seguro drenar.

Un rolling update manda SIGTERM y la réplica vieja sigue con su websocket de
Discord abierto hasta que la plataforma la mata. Hoy eso corta los turnos en
vuelo a media pipeline; la cura obvia —subir ``terminationGracePeriodSeconds``—
es la que NO se puede aplicar sola, porque una réplica vieja que sigue
*recibiendo* mientras la nueva ya conectó son dos bots con el mismo token
contestando lo mismo: el usuario ve cada respuesta dos veces.

Por eso el gate es prerequisito del grace period, no un complemento. ``TurnGate``
tiene exactamente dos responsabilidades:

1. **Dejar de admitir turnos nuevos** en cuanto se cierra (``close``). Los dos
   puntos de entrada guardados del gateway — ``PersonaClient._dispatch`` (la
   @mención y el edit-summon) y ``PersonaClient.dispatch_invite`` (el camino del
   host, con y sin ``wait``) — piden ficha antes de trabajar y se van sin ruido
   si no la hay.
2. **Esperar a los que ya están adentro** (``drain``), con un tope duro. Un turno
   que ya entregó texto a un humano no se puede cancelar; lo único que se puede
   hacer es dejarlo aterrizar.

El tope duro es lo que impide que la promesa se vuelva un cuelgue: vencido el
plazo se cierra igual y ``drain`` devuelve **quiénes quedaron vivos**, para que
el abandono se cuente en un evento estructurado en vez de desaparecer. Un
abandono silencioso es peor que uno contado.

El objeto es de proceso, no de persona: el gateway hostea N bots en un solo
proceso y el SIGTERM llega una sola vez para todos.
"""

from __future__ import annotations

import asyncio
import itertools


class TurnGate:
    """Ledger de turnos en vuelo con una puerta que se cierra una sola vez.

    No es un semáforo: no limita concurrencia ni bloquea a nadie mientras está
    abierta. ``admit`` es O(1) y síncrono a propósito — un turno nunca espera por
    la puerta, sólo pregunta si sigue abierta.
    """

    def __init__(self) -> None:
        self._accepting = True
        self._inflight: dict[int, str] = {}
        self._tickets = itertools.count(1)
        # Se mantiene SET mientras no haya nadie adentro, para que `drain` sobre
        # un gateway ocioso no tenga que sondear.
        self._idle = asyncio.Event()
        self._idle.set()

    @property
    def accepting(self) -> bool:
        return self._accepting

    @property
    def inflight(self) -> int:
        return len(self._inflight)

    @property
    def inflight_labels(self) -> list[str]:
        return sorted(self._inflight.values())

    def admit(self, label: str) -> int | None:
        """Ficha para un turno nuevo, o ``None`` si la puerta ya se cerró.

        ``label`` identifica al turno en el log del abandono (``persona:kind``);
        no tiene que ser único.
        """
        if not self._accepting:
            return None
        ticket = next(self._tickets)
        self._inflight[ticket] = label
        self._idle.clear()
        return ticket

    def release(self, ticket: int | None) -> None:
        """Devuelve la ficha. Idempotente y tolerante a ``None`` para que el
        ``finally`` del llamador nunca tenga que preguntar."""
        if ticket is None:
            return
        self._inflight.pop(ticket, None)
        if not self._inflight:
            self._idle.set()

    def close(self) -> None:
        self._accepting = False

    async def drain(self, timeout_s: float) -> list[str]:
        """Cierra la puerta y espera a los de adentro; devuelve los ABANDONADOS.

        Lista vacía = drenó completo. Lista con elementos = venció el tope y esos
        turnos siguen vivos cuando el proceso está por morir; el llamador los
        cuenta en el log en vez de tragárselos.
        """
        self.close()
        if not self._inflight:
            return []
        try:
            await asyncio.wait_for(self._idle.wait(), timeout=timeout_s)
        except TimeoutError:
            return self.inflight_labels
        return []
