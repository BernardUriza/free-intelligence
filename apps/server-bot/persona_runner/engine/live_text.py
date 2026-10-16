"""El texto de la persona en vivo, sin que se asome un marcador a medias.

El cerebro escribe `[REACT:🔥]` y `[GIF: búsqueda]` dentro del texto; el
post-proceso de F5 los recorta sobre la respuesta COMPLETA (`persona_core.reactions`,
`persona_core.gifs`). Al streamear deltas, un marcador puede llegar partido en
dos pedazos ("[REA" + "CT:🔥]"), así que el filtro publica todo lo que ya no
puede ser marcador y RETIENE sólo el sufijo que todavía podría serlo — el mismo
algoritmo de `extractReasoningMiddleware` del AI SDK — y descarta el marcador
entero cuando cierra. Un `[` que no es marcador se publica en cuanto se sabe;
un marcador abierto que nunca cierra se suelta como texto pasado un tope, para
que un corchete suelto en prosa no detenga el stream.
"""

from __future__ import annotations

import re

__all__ = ["MAX_OPEN_MARKER", "MarkerFilter"]

_MARKER = re.compile(r"\[(?:REACT|GIF):[^\]]*\]", re.IGNORECASE)
_HEADS = ("[REACT:", "[GIF:")
MAX_OPEN_MARKER = 64


def _could_become_marker(held: str) -> bool:
    upper = held.upper()
    if any(head.startswith(upper) for head in _HEADS):
        return True
    return any(upper.startswith(head) for head in _HEADS) and len(held) < MAX_OPEN_MARKER


class MarkerFilter:
    def __init__(self) -> None:
        self._held = ""

    def feed(self, chunk: str) -> str:
        """El texto publicable tras sumar `chunk`; lo que sigue retenido puede
        aún ser un marcador."""
        self._held += chunk
        out: list[str] = []
        while self._held:
            cut = self._held.find("[")
            if cut < 0:
                out.append(self._held)
                self._held = ""
                break
            out.append(self._held[:cut])
            self._held = self._held[cut:]
            match = _MARKER.match(self._held)
            if match:
                self._held = self._held[match.end() :]
                continue
            if _could_become_marker(self._held):
                break
            out.append("[")
            self._held = self._held[1:]
        return "".join(out)

    def flush(self) -> str:
        """Al terminar el turno: lo retenido se publica, salvo un marcador que
        quedó abierto (empezaba como uno y nunca cerró), que se descarta."""
        held, self._held = self._held, ""
        return "" if held.upper().startswith(_HEADS) else held
