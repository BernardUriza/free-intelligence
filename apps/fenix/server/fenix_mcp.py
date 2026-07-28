"""MCP de Fénix — le da al modelo la única herramienta que le faltaba.

EL PROBLEMA QUE CIERRA. El modelo calculaba la cotización perfectamente y la
escribía en el chat, pero el expediente no se enteraba: los renglones había que
pasarlos a mano por API para poder generar el Excel. El círculo quedaba abierto
justo antes del entregable.

POR QUÉ UNA HERRAMIENTA Y NO DARLE `Bash`. Con Bash el modelo podría escribir el
archivo… y también cualquier otro. `ToolPolicy.companion()` se lo bloquea a
propósito (og118 #277). Una herramienta acotada le deja hacer EXACTAMENTE una
cosa — guardar el desglose en su expediente — y nada más. El Excel lo sigue
generando el servidor con el formato aprobado.

Transporte stdio con `python -m`, igual que las capabilities de fi-core, para no
inventar un mecanismo nuevo. El store se localiza por `FENIX_EXPEDIENTES_PATH`,
la misma variable que usa el servidor.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated, Any

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from expedientes import ExpedienteStore

MCP_SERVER_NAME = "fenix-expedientes"
MCP_TOOLS = ("guardar_cotizacion",)

mcp = FastMCP(MCP_SERVER_NAME)


def _store() -> ExpedienteStore:
    ruta = os.getenv("FENIX_EXPEDIENTES_PATH") or str(Path.home() / ".fenix-data" / "expedientes.json")
    return ExpedienteStore(ruta)


@mcp.tool()
def guardar_cotizacion(
    conversacion_id: Annotated[str, Field(description="El id de esta conversación.")],
    alumno: Annotated[str, Field(description="Nombre del alumno.")] = "",
    escuela: Annotated[str, Field(description="Escuela, sin el grado.")] = "",
    grado: Annotated[str, Field(description="Grado y grupo, ej. 4°B.")] = "",
    tutor: Annotated[str, Field(description="Mamá, papá o tutor.")] = "",
    whatsapp: Annotated[str, Field(description="WhatsApp de contacto.")] = "",
    folio: Annotated[str, Field(description="Folio, si la lista lo trae.")] = "",
    descuento: Annotated[float, Field(description="Descuento aplicado: 0.15, 0.10, 0.08…")] = 0.15,
    items: Annotated[
        list[dict[str, Any]],
        Field(description="Renglones cotizados: descripcion, cantidad, precio DE LISTA (sin descuento)."),
    ] = [],
    forrado: Annotated[
        list[dict[str, Any]], Field(description="Renglones de forrado, misma forma que items.")
    ] = [],
    opcionales: Annotated[
        list[dict[str, Any]],
        Field(description="Se muestran con su costo pero NO suman al total (rótulos, etiquetas)."),
    ] = [],
    fuera: Annotated[
        list[str], Field(description="Artículos que Fénix no maneja, sólo la descripción.")
    ] = [],
) -> str:
    """Guarda el desglose de la cotización en el expediente del cliente.

    Llámala SIEMPRE que cierres una cotización, en el mismo turno en que das el
    total. Sin esto el presupuesto vive sólo en el chat y no se puede generar el
    Excel que se le manda a la mamá.

    Los precios van de LISTA, sin descuento: la hoja aplica el porcentaje sola.
    """
    total = sum(float(r.get("cantidad", 1)) * float(r.get("precio", 0)) for r in [*items, *forrado])
    guardado = _store().guardar(
        # El principal del servidor en modo bearer. Mismo dueño que el resto de
        # los expedientes; si algún día hay cuentas, esto se toma del contexto.
        os.getenv("FENIX_MCP_OWNER", "legacy-bearer"),
        {
            "conversacionId": conversacion_id,
            "alumno": alumno,
            "escuela": escuela,
            "grado": grado,
            "tutor": tutor,
            "whatsapp": whatsapp,
            "folio": folio,
            "estado": "entregada" if items else "cotizando",
            "total": round(total * (1 - descuento), 2) if items else None,
            "items": items,
            "forrado": forrado,
            "opcionales": opcionales,
            "fuera": fuera,
        },
    )
    renglones = len(guardado.get("items", [])) + len(guardado.get("forrado", []))
    return (
        f"Cotización guardada en el expediente de {guardado['alumno'] or 'cliente sin nombre'}: "
        f"{renglones} renglones, total ${guardado['total']}. "
        "Ya se puede descargar el Excel desde Expedientes."
    )


if __name__ == "__main__":
    mcp.run()
