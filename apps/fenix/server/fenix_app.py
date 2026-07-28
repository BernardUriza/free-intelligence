"""Entrypoint del servidor de Fénix.

NO es un servidor nuevo: importa la app de og118 tal cual — mismo `/chat/stream`,
mismo RAG, mismas conversaciones — y le monta encima el único router que es
específico de la papelería, el de expedientes. og118 no se entera de que existe
una papelería, y fenix no duplica 4,438 líneas para agregar una tabla.

Correr con:
    cd apps/og118/server
    FI_PERSONA_PATH=<repo>/apps/fenix/server/prompts/persona.md \
    FENIX_EXPEDIENTES_PATH=$HOME/.fenix-data/expedientes.json \
    ./.venv/bin/uvicorn --app-dir <repo>/apps/fenix/server fenix_app:app --port 8119

El módulo NO puede llamarse `app.py`: haría `from app import …` sobre sí mismo
(import circular), porque el directorio de og118 entra al path DESPUÉS del
propio. De ahí el nombre `fenix_app`.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# El runtime de og118 es el que se reusa; su directorio entra al path para poder
# importarlo sin instalarlo como paquete.
OG118 = Path(__file__).resolve().parents[2] / "og118" / "server"
if str(OG118) not in sys.path:
    sys.path.insert(0, str(OG118))

from fastapi import APIRouter, Depends, HTTPException  # noqa: E402
from fastapi.responses import Response  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from app import Principal, app, get_principal  # noqa: E402  (la app de og118)

from expedientes import ESTADOS, ExpedienteStore, id_valido  # noqa: E402
from presupuesto import Presupuesto, Renglon, a_vista, generar, nombre_archivo  # noqa: E402

_store: ExpedienteStore | None = None


def get_store() -> ExpedienteStore:
    global _store
    if _store is None:
        ruta = os.getenv("FENIX_EXPEDIENTES_PATH") or str(
            Path(os.getenv("OG118_PROJECT_REGISTRY_PATH", "expedientes.json")).parent
            / "expedientes.json"
        )
        _store = ExpedienteStore(ruta)
    return _store


class ExpedienteRequest(BaseModel):
    id: str | None = None
    conversacionId: str | None = None
    alumno: str = ""
    escuela: str = ""
    grado: str = ""
    tutor: str = ""
    whatsapp: str = ""
    folio: str = ""
    estado: str = "nueva"
    total: float | None = None
    notas: str = ""
    items: list[dict] = []
    forrado: list[dict] = []
    opcionales: list[dict] = []
    fuera: list[str] = []


router = APIRouter(prefix="/expedientes", tags=["fenix"])


@router.get("")
async def listar(
    principal: Principal = Depends(get_principal),
    store: ExpedienteStore = Depends(get_store),
) -> dict:
    return {"expedientes": store.listar(principal.sub), "estados": list(ESTADOS)}


@router.put("")
async def guardar(
    req: ExpedienteRequest,
    principal: Principal = Depends(get_principal),
    store: ExpedienteStore = Depends(get_store),
) -> dict:
    try:
        return store.guardar(principal.sub, req.model_dump())
    except PermissionError:
        # Igual que en conversaciones: un expediente ajeno es indistinguible de
        # uno inexistente, para no filtrar qué ids existen en otras cuentas.
        raise HTTPException(status_code=404, detail="expediente no encontrado")


@router.delete("/{expediente_id}")
async def borrar(
    expediente_id: str,
    principal: Principal = Depends(get_principal),
    store: ExpedienteStore = Depends(get_store),
) -> dict:
    if not id_valido(expediente_id):
        raise HTTPException(status_code=422, detail="id inválido")
    store.borrar(principal.sub, expediente_id)
    return {"borrado": expediente_id}


class RenglonRequest(BaseModel):
    descripcion: str
    cantidad: float = 1
    precio: float = 0


class PresupuestoRequest(BaseModel):
    alumno: str = ""
    escuela: str = ""
    grado: str = ""
    tutor: str = ""
    fecha: str = ""
    descuento: float = 0.15
    items: list[RenglonRequest] = []
    forrado: list[RenglonRequest] = []
    opcionales: list[RenglonRequest] = []
    fuera: list[str] = []


def _a_presupuesto(req: "PresupuestoRequest") -> Presupuesto:
    conv = lambda rs: [Renglon(r.descripcion, r.cantidad, r.precio) for r in rs]  # noqa: E731
    return Presupuesto(
        alumno=req.alumno, escuela=req.escuela, grado=req.grado, tutor=req.tutor,
        fecha=req.fecha, descuento=req.descuento,
        items=conv(req.items), forrado=conv(req.forrado),
        opcionales=conv(req.opcionales), fuera=list(req.fuera),
    )


@router.post("/excel/vista")
async def excel_vista(
    req: "PresupuestoRequest",
    _: Principal = Depends(get_principal),
) -> dict:
    """La hoja parseada para el visor del navegador.

    Genera el MISMO archivo que la descarga y lo parsea: la vista previa es el
    archivo, no una re-interpretación de los datos. Si divergieran, el usuario
    confiaría en una hoja que no es la que manda.
    """
    if not req.items and not req.forrado:
        raise HTTPException(status_code=422, detail="un presupuesto sin renglones no es un presupuesto")
    p = _a_presupuesto(req)
    return {"nombre": nombre_archivo(p), **a_vista(generar(p))}


@router.post("/excel")
async def excel(
    req: PresupuestoRequest,
    _: Principal = Depends(get_principal),
) -> Response:
    """El presupuesto en .xlsx — el entregable que se manda por WhatsApp.

    Lo genera el SERVIDOR, no el modelo: `ToolPolicy.companion()` le bloquea
    Bash/Write al agente (y debe seguir así), y además el formato es el aprobado
    por la dirección — si lo ejecutara el modelo, podría improvisarlo.
    """
    if not req.items and not req.forrado:
        raise HTTPException(status_code=422, detail="un presupuesto sin renglones no es un presupuesto")

    p = _a_presupuesto(req)
    datos = generar(p)
    return Response(
        content=datos,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{nombre_archivo(p)}"',
            # Sin esto el navegador OCULTA el header al JavaScript por CORS y la
            # descarga sale como "Presupuesto.xlsx" genérico. El archivo se manda
            # por WhatsApp: su nombre tiene que decir de quién es sin abrirlo.
            "Access-Control-Expose-Headers": "Content-Disposition",
        },
    )


app.include_router(router)
