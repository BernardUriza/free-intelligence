"""Per-principal rate limit for the voice endpoints.

POR QUÉ EXISTE, con el número medido (2026-09-09). `/stt/transcribe` y
`/tts/synthesize` proxean el gateway susurro, cuyo upstream de Azure aprovisiona
por REQUESTS POR MINUTO: los deployments `whisper` y `tts` están en `capacity: 3`
—3 RPM cada uno— y ése es el techo duro de la suscripción en northcentralus
(`az cognitiveservices usage list` → whisper 3.0/3.0, tts 3.0/3.0; subirlo exige
una solicitud de cuota a Azure). Ese gateway es COMPARTIDO: discord-bot, inkbook,
picturelock, visalaw-videopipe y el dictado de un tiro de og118 beben del mismo
techo.

Sin este tope, un solo llamante puede consumirlo entero y dejar sin voz a toda la
flota. El límite por default IGUALA el techo upstream (3/min) a propósito: no
inventa una restricción que el upstream no impondría ya —eso rompería el dictado
de un tiro, que funciona hoy— pero convierte un 429 caro y remoto en uno local,
honesto y con `Retry-After`.

El contador es POR RÉPLICA (en proceso). Con más de una réplica el techo efectivo
se multiplica; decirlo aquí es más honesto que fingir un límite global que este
proceso no puede sostener.
"""

from __future__ import annotations

import os
import time
from collections import defaultdict, deque

from fastapi import HTTPException

VENTANA_SEGUNDOS = 60.0


def limite_por_minuto() -> int:
    """`OG118_VOICE_RPM`, o el techo upstream. 0 desactiva el tope."""
    try:
        return max(0, int(os.getenv("OG118_VOICE_RPM", "3")))
    except ValueError:
        return 3


class ContadorDeVoz:
    """Ventana deslizante de un minuto por sujeto. Sin candado: el event loop de
    FastAPI es de un solo hilo, así que un `append` no se intercala."""

    def __init__(self) -> None:
        self._marcas: dict[str, deque[float]] = defaultdict(deque)

    def registrar(self, sujeto: str, limite: int, ahora: float | None = None) -> float:
        """Anota una llamada. Devuelve 0.0 si cabe; si no, los segundos que
        faltan para que el hueco más viejo salga de la ventana."""
        if limite <= 0:
            return 0.0
        t = time.monotonic() if ahora is None else ahora
        marcas = self._marcas[sujeto]
        while marcas and t - marcas[0] >= VENTANA_SEGUNDOS:
            marcas.popleft()
        if len(marcas) >= limite:
            return max(1.0, VENTANA_SEGUNDOS - (t - marcas[0]))
        marcas.append(t)
        return 0.0


_contador = ContadorDeVoz()


def verificar_cuota_de_voz(sujeto: str) -> None:
    """Anota la llamada de `sujeto`; 429 con `Retry-After` si se pasó.

    Función, no dependencia de FastAPI: `get_principal` vive en `app.py`, así que
    componerla como `Depends` cerraría un ciclo de imports. El endpoint ya tiene
    su principal — llamarla es una línea.
    """
    limite = limite_por_minuto()
    espera = _contador.registrar(sujeto, limite)
    if espera:
        raise HTTPException(
            status_code=429,
            detail={
                "code": "VOICE_RATE_LIMITED",
                "message": (
                    f"Demasiadas peticiones de voz. Máximo {limite} por minuto; "
                    f"reintenta en {int(espera)} s."
                ),
            },
            headers={"Retry-After": str(int(espera))},
        )
