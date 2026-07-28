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
from typing import Any
from pathlib import Path

# El runtime de og118 es el que se reusa; su directorio entra al path para poder
# importarlo sin instalarlo como paquete.
OG118 = Path(__file__).resolve().parents[2] / "og118" / "server"
if str(OG118) not in sys.path:
    sys.path.insert(0, str(OG118))

from fastapi import APIRouter, Depends, HTTPException  # noqa: E402
from fastapi.responses import Response  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from app import (  # noqa: E402  (la app de og118)
    Principal,
    app,
    get_conversation_store,
    get_principal,
)
from runner import build_runner  # noqa: E402

from expedientes import ESTADOS, ExpedienteStore, id_valido  # noqa: E402
from presupuesto import Presupuesto, Renglon, a_vista, generar, nombre_archivo  # noqa: E402
from rbac import es_admin, modo_abierto  # noqa: E402

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


def solo_admin(principal: Principal = Depends(get_principal)) -> Principal:
    """Puerta de los expedientes.

    404 y no 403 a propósito: para un caller del cibercafé, la superficie de
    administración no existe. Un 403 confirmaría que hay algo detrás.
    """
    if not es_admin(principal):
        raise HTTPException(status_code=404, detail="no encontrado")
    return principal


@router.get("/rol")
async def rol(principal: Principal = Depends(get_principal)) -> dict:
    """Qué puede hacer quien pregunta. El frontend pinta según esto."""
    return {
        "admin": es_admin(principal),
        "email": principal.email,
        "modoAbierto": modo_abierto(),
    }


@router.get("")
async def listar(
    principal: Principal = Depends(solo_admin),
    store: ExpedienteStore = Depends(get_store),
) -> dict:
    return {"expedientes": store.listar(principal.sub), "estados": list(ESTADOS)}


@router.put("")
async def guardar(
    req: ExpedienteRequest,
    principal: Principal = Depends(solo_admin),
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
    principal: Principal = Depends(solo_admin),
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
    # Sin default silencioso: el descuento pactado viaja con el expediente. Una
    # cotización al 10% impresa al 15% es un total equivocado en el archivo que
    # el cliente recibe.
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
    _: Principal = Depends(solo_admin),
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
    _: Principal = Depends(solo_admin),
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


def _campo(objeto: Any, nombre: str) -> str:
    """Lee un campo tanto de un dict como de una dataclass del stream."""
    if objeto is None:
        return ""
    if isinstance(objeto, dict):
        return str(objeto.get(nombre) or "")
    return str(getattr(objeto, nombre, "") or "")


class ExtraerRequest(BaseModel):
    conversacion_id: str
    corpus_id: str = ""


@router.post("/extraer")
async def extraer(
    req: ExtraerRequest,
    principal: Principal = Depends(solo_admin),
    convs=Depends(get_conversation_store),
) -> dict:
    """Rellena el expediente leyendo una conversación YA existente.

    Las 33 cotizaciones migradas de claude.ai tienen su desglose escrito en el
    hilo, no en campos: el modelo lo calculó ahí. Este endpoint le pide que lo
    lea y lo guarde con `guardar_cotizacion` — la misma herramienta que usa al
    cotizar en vivo, para que la extracción y el flujo normal produzcan
    exactamente la misma forma de dato.

    Un turno del modelo por conversación: es caro, así que se dispara a
    petición y de una en una, nunca en un barrido automático.
    """
    registro = convs.get(principal.sub, req.conversacion_id)
    if registro is None:
        raise HTTPException(status_code=404, detail="conversación no encontrada")

    mensajes = registro.get("messages") or []
    if not mensajes:
        raise HTTPException(status_code=422, detail="la conversación está vacía")

    # El hilo COMPLETO, no los últimos mensajes. El desglose con todos los
    # renglones aparece en el turno donde se cotiza —normalmente el primero— y
    # después vienen sólo correcciones puntuales ("las fichas ponlas a 85"). Una
    # ventana de los últimos N mensajes deja al modelo viendo las correcciones
    # sin la lista que corrigen: probado con la conversación de estela quiroz,
    # respondió SIN_COTIZACION teniendo el presupuesto completo más arriba.
    partes = [f"[{m.get('role')}] {str(m.get('content') or '')[:6000]}" for m in mensajes]
    hilo = "\n\n".join(partes)
    if len(hilo) > 60000:  # cota de seguridad para un hilo excepcionalmente largo
        hilo = hilo[:30000] + "\n\n[…]\n\n" + hilo[-30000:]

    instruccion = (
        "TAREA ÚNICA, SIN PREÁMBULO. No expliques lo que vas a hacer, no declares un "
        "plan y no escribas la cotización en tu respuesta: la única salida válida de "
        "este turno es UNA llamada a la herramienta `mcp__fenix-expedientes__guardar_cotizacion` "
        "(búscala con ToolSearch por ese nombre exacto si no la ves; SÍ está disponible) "
        "o la palabra SIN_COTIZACION "
        "si no aplica). Llama la herramienta ANTES de escribir cualquier texto.\n\n"
        "Reconstruye el presupuesto que quedó vigente en esta conversación y guárdalo "
        f'con `mcp__fenix-expedientes__guardar_cotizacion`, conversacion_id="{req.conversacion_id}".\n\n'
        "REGLAS DE LA RECONSTRUCCIÓN:\n"
        "- Toma la versión FINAL: si hubo correcciones ('las fichas ponlas a 85'), gana "
        "la corrección, no el valor original.\n"
        "- Los precios van de LISTA, sin descuento. Si en el hilo sólo aparece el precio "
        "ya rebajado, divídelo entre (1 − descuento) para volver al de lista.\n"
        "- Un desglose PARCIAL es útil y se guarda igual: guarda los renglones que sí "
        "puedas identificar. No hace falta que estén los 20 para llamar la herramienta.\n"
        "- Lo que la conversación marcó como 'falta precio' o que Fénix no maneja va en "
        "`fuera`, sin precio. Los rótulos y etiquetas van en `opcionales`.\n"
        "- NO inventes renglones que no aparezcan en el hilo, y no consultes la lista "
        "maestra para completar lo que el cliente nunca pidió.\n"
        "- Pasa SIEMPRE `total_declarado` con el total que la conversación dice que se le "
        "dio al cliente. Si tu desglose no llega a esa cifra, el expediente se marca como "
        "incompleto — que es exactamente lo que queremos: mejor saberlo que mandar un "
        "Excel con un total que no es el que se cotizó.\n\n"
        "Sólo responde SIN_COTIZACION —sin llamar la herramienta— si el hilo no es una "
        "cotización en absoluto (una consulta suelta de precios, una prueba, un trámite).\n\n"
        f"--- CONVERSACIÓN ---\n{hilo}"
    )

    runner = build_runner()
    texto = ""
    herramientas: list[str] = []
    contexto = {"corpus_id": req.corpus_id} if req.corpus_id else None
    async for ev in runner.run_stream(
        instruccion, session_id=f"extraer-{req.conversacion_id}", context=contexto
    ):
        tipo = ev.get("type")
        if tipo == "text":
            texto += ev.get("text") or ""
        elif tipo == "result":
            # El stream mezcla dicts y dataclasses (TurnResult): se lee por
            # atributo o por clave, sin asumir cuál toca.
            texto = _campo(ev.get("result"), "text") or texto
        elif tipo == "tool_call":
            herramientas.append(_campo(ev.get("tool") or ev.get("call"), "name") or "")

    guardo = any("guardar_cotizacion" in h for h in herramientas)
    return {
        "conversacion_id": req.conversacion_id,
        "titulo": registro.get("title"),
        "guardado": guardo,
        "motivo": None if guardo else texto.strip()[:220],
    }


app.include_router(router)
