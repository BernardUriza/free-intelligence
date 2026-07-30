"""Expedientes de Fénix — el cliente escolar como objeto, no como etiqueta.

Hasta el 27-jul el expediente vivía dentro del TÍTULO de la conversación
(`fecha — alumno (escuela) — WhatsApp`). Era la convención que el equipo ya
usaba a mano y funcionó para arrancar, pero el título es un contenedor de 60
caracteres (`TITLE_MAX` en fi-core, que trunca sin avisar): para que cupiera el
teléfono hubo que abreviar la escuela con elipsis. Un contenedor donde un campo
se mutila para salvar otro no es un expediente.

Aquí el expediente tiene campos propios y el título del chat se DERIVA de él.
Sigue el molde de `og118/server/projects.py`: JSON en disco, un solo escritor,
escritura atómica (temp + os.replace) bajo lock, y todo scoped por dueño.
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import re
import threading
import uuid
from pathlib import Path
from typing import Any

_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

# Los estados reales observados en las 33 sesiones migradas, en el orden en que
# ocurren en el mostrador. `bloqueada` existe porque la auditoría encontró que
# la mayoría de las cotizaciones se quedaban esperando un dato, y eso merece ser
# un estado visible y no una nota perdida en el hilo.
ESTADOS = ("nueva", "cotizando", "bloqueada", "entregada", "cerrada")


def id_valido(valor: str) -> bool:
    return bool(_ID_RE.match(valor))


def _renglones(valor: Any) -> list[dict]:
    """Normaliza los renglones que vengan del cliente o del modelo."""
    salida = []
    for r in valor or []:
        if not isinstance(r, dict):
            continue
        desc = str(r.get("descripcion") or "").strip()
        if not desc:
            continue
        try:
            cant = float(r.get("cantidad") or 1)
            precio = float(r.get("precio") or 0)
        except (TypeError, ValueError):
            continue
        salida.append({"descripcion": desc, "cantidad": cant, "precio": precio})
    return salida


def _ahora() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat()


class ExpedienteStore:
    def __init__(self, path: str | os.PathLike) -> None:
        self._path = Path(path)
        self._lock = threading.Lock()
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> dict[str, dict]:
        try:
            return json.loads(self._path.read_text("utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save(self, data: dict[str, dict]) -> None:
        tmp = self._path.with_suffix(self._path.suffix + ".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False), "utf-8")
        os.replace(tmp, self._path)  # atómico en POSIX

    @staticmethod
    def _completo(e: dict) -> dict:
        """Rellena los campos que un registro viejo no tenía.

        Los 33 expedientes migrados se escribieron antes de que existieran los
        renglones; sin esto el cliente recibe `items: undefined` y revienta al
        leer `.length`. Un store que gana campos con el tiempo debe devolver
        siempre la forma completa.
        """
        for k in ("items", "forrado", "opcionales", "fuera"):
            e.setdefault(k, [])
        e.setdefault("descuento", 0.15)
        e.setdefault("totalDeclarado", None)
        e.setdefault("desgloseIncompleto", False)
        return e

    def listar(self, owner: str) -> list[dict]:
        vivos = [self._completo(e) for e in self._load().values() if e.get("ownerId") == owner]
        return sorted(vivos, key=lambda e: e.get("actualizado") or "", reverse=True)

    def obtener(self, owner: str, expediente_id: str) -> dict | None:
        e = self._load().get(expediente_id)
        return e if e and e.get("ownerId") == owner else None

    def guardar(self, owner: str, datos: dict[str, Any]) -> dict:
        """Alta o actualización. El id lo pone el servidor salvo que ya exista.

        Un expediente se identifica por su `conversacionId` cuando viene de un
        chat: así la cotización y su expediente no se duplican si alguien guarda
        dos veces desde la misma conversación.
        """
        with self._lock:
            data = self._load()
            eid = str(datos.get("id") or "").strip()
            if not eid or not id_valido(eid):
                conv = str(datos.get("conversacionId") or "").strip()
                previo = next(
                    (
                        e
                        for e in data.values()
                        if conv and e.get("conversacionId") == conv and e.get("ownerId") == owner
                    ),
                    None,
                )
                eid = previo["id"] if previo else f"exp-{uuid.uuid4()}"

            anterior = data.get(eid)
            if anterior and anterior.get("ownerId") != owner:
                raise PermissionError("expediente ajeno")

            estado = str(datos.get("estado") or "nueva")
            if estado not in ESTADOS:
                estado = "nueva"

            # `bloqueada` es una CONSECUENCIA de que falten datos, no una etiqueta
            # que alguien mantiene a mano. Si se deja manual, el tablero miente en
            # cuanto alguien completa el expediente y no se acuerda de cambiar el
            # estado — y el filtro "Falta info" es justo el que se usa para saber
            # qué cotización está detenida.
            completo = bool(str(datos.get("alumno") or "").strip()) and bool(
                str(datos.get("whatsapp") or "").strip()
            )
            if not completo and estado in ("nueva", "cotizando"):
                estado = "bloqueada"
            elif completo and estado == "bloqueada":
                estado = "cotizando"

            # Un desglose que no llega al total que se le dio al cliente es una
            # trampa: el Excel saldría con una cifra menor y parecería correcto.
            # Se marca para que la UI lo advierta en vez de dejar mandar el
            # archivo a ciegas.
            declarado = datos.get("totalDeclarado")
            items_norm = _renglones(datos.get("items"))
            forrado_norm = _renglones(datos.get("forrado"))
            suma = sum(r["cantidad"] * r["precio"] for r in [*items_norm, *forrado_norm])
            try:
                descuento = float(datos.get("descuento"))
            except (TypeError, ValueError):
                descuento = 0.15
            calculado = round(suma * (1 - descuento), 2)
            incompleto = False
            if declarado:
                try:
                    incompleto = abs(float(declarado) - calculado) > 1.0
                except (TypeError, ValueError):
                    incompleto = False

            expediente = {
                "id": eid,
                "ownerId": owner,
                "conversacionId": (datos.get("conversacionId") or None),
                "alumno": (datos.get("alumno") or "").strip(),
                "escuela": (datos.get("escuela") or "").strip(),
                "grado": (datos.get("grado") or "").strip(),
                "tutor": (datos.get("tutor") or "").strip(),
                "whatsapp": (datos.get("whatsapp") or "").strip(),
                "folio": (datos.get("folio") or "").strip(),
                "estado": estado,
                "total": datos.get("total"),
                "descuento": descuento,
                # Los renglones de la cotización. Viven aquí y no sólo en el
                # hilo porque el Excel se genera del expediente: si el dato
                # está únicamente en la conversación, el entregable depende de
                # volver a pedírselo al modelo cada vez.
                "items": items_norm,
                "forrado": forrado_norm,
                "opcionales": _renglones(datos.get("opcionales")),
                "fuera": [str(x).strip() for x in (datos.get("fuera") or []) if str(x).strip()],
                "notas": (datos.get("notas") or "").strip(),
                "totalDeclarado": declarado,
                "desgloseIncompleto": incompleto,
                "creado": (anterior or {}).get("creado") or _ahora(),
                "actualizado": _ahora(),
            }
            data[eid] = expediente
            self._save(data)
        return expediente

    def borrar(self, owner: str, expediente_id: str) -> None:
        with self._lock:
            data = self._load()
            e = data.get(expediente_id)
            if e and e.get("ownerId") == owner:
                del data[expediente_id]
                self._save(data)
