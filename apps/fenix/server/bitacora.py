"""La bitácora del cibercafé — qué se preguntó, desde dónde y cuánto costó.

El `/chat/stream` público es la única superficie de Fénix que gasta dinero, y
hasta ahora no dejaba rastro: el log del contenedor sólo dice
`POST /chat/stream 200`, sin quién ni qué, y encima con la IP interna del
ingress en vez de la del visitante. Si alguien encontrara la URL y la usara
para lo que fuera, la primera señal sería la factura.

Un límite de gasto sin registro es media protección: la cuota impide que el
daño sea grande, pero no permite saber que ocurrió, ni distinguir a un niño
haciendo tarea de un script. Esto es la otra mitad.

## Qué se guarda, y por qué tan poco

Una línea JSON por turno, `append-only`:

- **cuándo** (UTC) y **desde qué IP** — la real del visitante, no la del proxy.
- **rol** (`mostrador` o `publico`) y si el turno se **cortó por cuota**.
- **la pregunta, recortada** a `LIMITE_TEXTO`. Son niños haciendo tarea: el
  texto sirve para reconocer un patrón de abuso ("mil turnos iguales a las 3
  de la mañana") y para ver qué necesitan de verdad. No se guarda la respuesta
  del modelo — abulta y no responde ninguna de las dos preguntas.

No se guarda ningún nombre: la papelería ya tiene los expedientes para eso, y
la bitácora la puede leer cualquiera del mostrador.

## Por qué JSONL en el volumen y no una base

Cabe en el mismo Azure Files que ya está montado, se lee con `tail`, sobrevive
al redeploy y no agrega una dependencia para escribir una línea por turno. Rota
sola al pasar de `MAX_BYTES` para no llenar el disco del negocio; se conserva
UNA generación anterior, que es lo que se necesita para investigar algo que
pasó ayer.
"""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path

LIMITE_TEXTO = 300
MAX_BYTES = 5 * 1024 * 1024


def ruta_por_defecto() -> Path:
    declarada = os.getenv("FENIX_BITACORA_PATH")
    if declarada:
        return Path(declarada)
    return Path(os.getenv("FENIX_EXPEDIENTES_PATH") or Path.home() / ".fenix-data" / "x").parent / "bitacora.jsonl"


class Bitacora:
    """Append-only, con un candado porque el servidor corre en una sola réplica
    pero con varios hilos atendiendo."""

    def __init__(self, path: str | os.PathLike | None = None) -> None:
        self._path = Path(path) if path else ruta_por_defecto()
        self._candado = threading.Lock()

    @property
    def path(self) -> Path:
        return self._path

    def anotar(
        self,
        *,
        ip: str,
        rol: str,
        texto: str | None = None,
        cortado: bool = False,
        extra: dict | None = None,
    ) -> None:
        """Nunca revienta el turno.

        Un fallo al escribir la bitácora —disco lleno, permisos, el volumen que
        no montó— no puede dejar sin respuesta al niño que preguntó. Se registra
        lo que se pueda y el turno sigue.
        """
        linea = {
            "cuando": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "ip": ip,
            "rol": rol,
            "cortado": cortado,
        }
        if texto:
            recorte = texto.strip().replace("\n", " ")
            linea["texto"] = recorte[:LIMITE_TEXTO]
            if len(recorte) > LIMITE_TEXTO:
                linea["texto_largo"] = len(recorte)
        if extra:
            linea.update(extra)
        try:
            with self._candado:
                self._rotar_si_toca()
                self._path.parent.mkdir(parents=True, exist_ok=True)
                with self._path.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(linea, ensure_ascii=False) + "\n")
        except Exception:  # noqa: BLE001 — ver el docstring
            pass

    def _rotar_si_toca(self) -> None:
        try:
            if self._path.exists() and self._path.stat().st_size >= MAX_BYTES:
                self._path.replace(self._path.with_suffix(".jsonl.1"))
        except OSError:
            pass

    def leer(self, limite: int = 200) -> list[dict]:
        """Los últimos `limite` turnos, del más reciente al más viejo."""
        try:
            with self._path.open(encoding="utf-8") as f:
                lineas = f.readlines()[-limite:]
        except FileNotFoundError:
            return []
        except OSError:
            return []
        salida = []
        for cruda in reversed(lineas):
            try:
                salida.append(json.loads(cruda))
            except json.JSONDecodeError:
                continue
        return salida

    def resumen(self, limite: int = 2000) -> dict:
        """Lo que se mira primero: cuánto se usó y desde cuántos lugares.

        Una IP desconocida con muchos turnos es la señal que esta bitácora
        existe para dar.
        """
        turnos = self.leer(limite)
        por_ip: dict[str, int] = {}
        cortados = 0
        for t in turnos:
            por_ip[t.get("ip", "?")] = por_ip.get(t.get("ip", "?"), 0) + 1
            if t.get("cortado"):
                cortados += 1
        return {
            "turnos": len(turnos),
            "cortados_por_cuota": cortados,
            "por_ip": dict(sorted(por_ip.items(), key=lambda kv: -kv[1])),
            "desde": turnos[-1]["cuando"] if turnos else None,
            "hasta": turnos[0]["cuando"] if turnos else None,
        }
