"""Cuota de turnos — lo que impide que la superficie pública vacíe la cuota del modelo.

POR QUÉ NO BASTA AUTENTICAR. El reflejo ante "cualquiera puede gastar mi cuota"
es pedir credencial. Aquí no alcanza: la superficie pública ES una máquina donde
cualquiera se sienta, así que el bearer vive en su localStorage y se saca con
F12. Autenticar sirve contra el escaneo de internet —vale la pena— pero no
contra quien se sienta en la PC ni contra quien copie el token y la llame desde
fuera. Lo que acota el gasto es un presupuesto por quien llama.

POR QUÉ EN MEMORIA. El servidor se despliega con `--min-replicas 1
--max-replicas 1` (DEPLOY.md: las sesiones son en memoria por réplica), así que
hay exactamente un proceso y este contador ES el contador global. Con varias
réplicas habría que moverlo a un store compartido; mientras la topología sea
ésa, meter Redis sería infraestructura para un problema que no existe.

EL MOSTRADOR NO SE LIMITA. Cotizar una lista de treinta artículos son muchos
turnos seguidos, y una papelería frenada a media venta es un daño peor que el
que esto previene.
"""

from __future__ import annotations

import os
import time
from collections import deque


class CuotaAgotada(Exception):
    """Quien llama pasó su presupuesto. Lleva cuántos segundos faltan."""

    def __init__(self, segundos: int) -> None:
        super().__init__(f"cuota agotada, reintenta en {segundos}s")
        self.segundos = segundos


class Cuota:
    """Ventana deslizante por clave: una ráfaga corta y un techo por hora.

    Dos ventanas y no una porque atacan cosas distintas: la de minuto frena un
    bucle que dispara sin parar, la de hora acota el total aunque el ritmo sea
    humano. Con sólo la de hora, un script gasta el presupuesto entero en
    segundos y deja la tarde muerta para quien sí la iba a usar.
    """

    def __init__(
        self,
        por_minuto: int,
        por_hora: int,
        *,
        max_claves: int = 512,
        reloj=time.monotonic,
    ) -> None:
        self.por_minuto = por_minuto
        self.por_hora = por_hora
        self.max_claves = max_claves
        self._reloj = reloj
        self._marcas: dict[str, deque[float]] = {}

    def _podar(self, marcas: deque[float], ahora: float) -> None:
        while marcas and ahora - marcas[0] > 3600:
            marcas.popleft()

    def consumir(self, clave: str) -> None:
        """Registra un turno de `clave`, o levanta CuotaAgotada sin registrarlo."""
        ahora = self._reloj()
        marcas = self._marcas.get(clave)
        if marcas is None:
            # Un atacante que rote la clave (cabeceras falsas) haría crecer este
            # dict sin techo. Al llenarse se tira la clave más vieja: se prefiere
            # perder memoria de un visitante antiguo antes que la memoria toda.
            if len(self._marcas) >= self.max_claves:
                mas_vieja = min(self._marcas, key=lambda k: self._marcas[k][-1])
                del self._marcas[mas_vieja]
            marcas = self._marcas[clave] = deque()

        self._podar(marcas, ahora)

        en_el_minuto = sum(1 for t in marcas if ahora - t <= 60)
        if en_el_minuto >= self.por_minuto:
            mas_viejo = next(t for t in marcas if ahora - t <= 60)
            raise CuotaAgotada(max(1, int(61 - (ahora - mas_viejo))))
        if len(marcas) >= self.por_hora:
            raise CuotaAgotada(max(1, int(3601 - (ahora - marcas[0]))))

        marcas.append(ahora)


def _entero(nombre: str, defecto: int) -> int:
    try:
        return max(1, int(os.getenv(nombre, "").strip() or defecto))
    except ValueError:
        return defecto


def cuota_publica() -> Cuota:
    """El presupuesto del cibercafé.

    Los defaults salen del uso real: dos PC, turnos de veinte minutos, unos diez
    mensajes por sesión. 60 por hora deja holgura de sobra para dos niños
    trabajando y aun así corta en seco un bucle que, sin esto, haría miles.

    **Los dos límites hacen cosas distintas y por eso no se mueven juntos.**
    Las dos PC del cibercafé salen por el mismo router, así que para la cuota
    son un solo cliente y comparten el cubo. El límite POR MINUTO es el que se
    siente en la sala —dos niños preguntando a la vez se estorban— y subirlo no
    sube el techo de gasto, sólo permite la ráfaga. El límite POR HORA sí ES el
    techo: 60 turnos/hora es lo máximo que alguien puede quemar en una hora, y
    ése no se toca a la ligera aunque haya contraseña, porque una contraseña que
    usan varios niños termina compartida.
    """
    return Cuota(
        por_minuto=_entero("FENIX_CUOTA_POR_MINUTO", 15),
        por_hora=_entero("FENIX_CUOTA_POR_HORA", 60),
    )


def clave_de(client_host: str | None, x_forwarded_for: str | None) -> str:
    """A quién se le cobra el turno.

    `X-Forwarded-For` lo puede escribir el cliente, así que confiar en él por
    default vuelve el límite evitable rotando una cabecera. Sólo se lee cuando
    el operador declara que hay un proxy delante (`FENIX_PROXY_CONFIABLE=1`).

    Sin esa declaración y detrás de un proxy, todos comparten un mismo cubo: es
    MÁS restrictivo, no menos. La falla se prefiere hacia el lado que no cuesta
    dinero.
    """
    if (os.getenv("FENIX_PROXY_CONFIABLE") or "").strip() in ("1", "true", "yes"):
        if x_forwarded_for:
            primero = x_forwarded_for.split(",")[0].strip()
            if primero:
                return primero
    return client_host or "desconocido"
