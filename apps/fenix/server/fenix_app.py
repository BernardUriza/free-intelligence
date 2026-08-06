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
import threading
from typing import Any
from pathlib import Path

# El runtime de og118 es el que se reusa; su directorio entra al path para poder
# importarlo sin instalarlo como paquete.
#
# La ruta es CONFIGURABLE porque el layout del monorepo no sobrevive al
# contenedor: en el repo, og118 está en `../og118/server` relativo a este
# archivo; en la imagen los dos viven en /opt/fi (`fenix` y `server`), así que
# el cálculo relativo apuntaba a un directorio inexistente y el arranque moría
# con `ModuleNotFoundError: No module named 'app'`. Sólo se veía desplegando.
OG118 = Path(
    os.environ.get("FI_OG118_DIR") or Path(__file__).resolve().parents[2] / "og118" / "server"
)
if not (OG118 / "app.py").exists():
    raise RuntimeError(
        f"no encuentro el runtime de og118 en {OG118}. Declara FI_OG118_DIR con la "
        "ruta del directorio que contiene app.py."
    )
if str(OG118) not in sys.path:
    sys.path.insert(0, str(OG118))

from fastapi import APIRouter, Depends, Header, HTTPException, Request  # noqa: E402
from fastapi.dependencies.utils import get_parameterless_sub_dependant  # noqa: E402
from fastapi.responses import Response  # noqa: E402
from fastapi.routing import APIRoute  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from app import (  # noqa: E402  (el runtime de og118)
    Principal,
    create_app,
    get_conversation_store,
    get_principal,
    get_runner_selector,
)

from fi_runner import load_prompt  # noqa: E402
from runner import build_runner  # noqa: E402

from expedientes import ESTADOS, ExpedienteStore, id_valido  # noqa: E402
from presupuesto import Presupuesto, Renglon, a_vista, generar, nombre_archivo  # noqa: E402
from cuota import CuotaAgotada, clave_de, cuota_publica  # noqa: E402
from arranque import exigir_config  # noqa: E402
from bitacora import Bitacora  # noqa: E402
from rbac import acceso_valido, correo_conocido, es_admin, hay_contrasena, modo_abierto  # noqa: E402

# Antes de montar nada. Dos configuraciones se ven idénticas a un servidor sano
# y no lo son: la que deja los expedientes abiertos y la que atiende a terceros
# con la suscripción personal. Revientan aquí, donde se ven.
exigir_config()

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


def solo_admin(x_fenix_admin: str | None = Header(default=None)) -> None:
    """Puerta de los expedientes: el token del mostrador.

    404 y no 403 a propósito: para una PC del cibercafé, la superficie de
    administración no existe. Un 403 confirmaría que hay algo detrás.
    """
    if not es_admin(x_fenix_admin):
        raise HTTPException(status_code=404, detail="no encontrado")


@router.get("/rol")
async def rol(
    x_fenix_admin: str | None = Header(default=None),
    x_fenix_email: str | None = Header(default=None),
) -> dict:
    """Qué puede hacer quien pregunta. El frontend pinta según esto."""
    admin = es_admin(x_fenix_admin)
    return {
        "admin": admin,
        "email": x_fenix_email,
        "correoConocido": correo_conocido(x_fenix_email) if admin else True,
        "modoAbierto": modo_abierto(),
    }


@router.get("/bitacora")
async def bitacora(
    limite: int = 200,
    _: None = Depends(solo_admin),
) -> dict:
    """Qué se ha preguntado en el cibercafé. Sólo desde el mostrador.

    El resumen va primero a propósito: lo que se mira al abrir esto no es la
    lista de preguntas, es si hay una IP desconocida acumulando turnos.
    """
    return {
        "resumen": _BITACORA.resumen(),
        "turnos": _BITACORA.leer(limite),
        "archivo": str(_BITACORA.path),
    }


@router.get("")
async def listar(
    principal: Principal = Depends(get_principal),
    _: None = Depends(solo_admin),
    store: ExpedienteStore = Depends(get_store),
) -> dict:
    return {"expedientes": store.listar(principal.sub), "estados": list(ESTADOS)}


@router.put("")
async def guardar(
    req: ExpedienteRequest,
    principal: Principal = Depends(get_principal),
    _: None = Depends(solo_admin),
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
    _: None = Depends(solo_admin),
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
    _: None = Depends(solo_admin),
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
    _: None = Depends(solo_admin),
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
    principal: Principal = Depends(get_principal),
    _: None = Depends(solo_admin),
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


# --- La puerta y el presupuesto, en UNA dependencia de la app ----------------
#
# Corre en toda ruta de ESTA instancia y sólo de ésta. Antes se mutaban los
# objetos APIRoute heredados de og118 para inyectarles la dependencia — eso
# dependía de que `include_router` los COPIARA, y FastAPI 0.141 dejó de
# hacerlo: dos apps que incluyen el mismo router comparten los MISMOS objetos.
# Con esa versión, la mutación le viajaba de vuelta a og118 y, peor, la
# búsqueda plana en `app.routes` encontraba cero rutas, así que ni la cuota ni
# la puerta se aplicaban. Se descubrió desplegando; en local la versión vieja
# seguía copiando y los tests pasaban.
#
# Una dependencia pasada al constructor no depende de ningún detalle interno:
# es la API pública para "esto aplica a toda mi app".
#
# El audio entra aquí porque quitar el bearer de og118 —que es lo que devuelve
# la palabra al cibercafé— lo dejaría sin ningún candado, y transcribir y
# sintetizar cuestan dinero por segundo. Ningún cliente de Fénix los llama: el
# niño escribe y lee. Si mañana el mostrador quiere dictado, ya pasa con su
# token; lo que no puede es quedar abierto a internet mientras nadie lo usa.
_RUTAS_DEL_MOSTRADOR = ("/conversations", "/projects", "/tts/synthesize", "/stt/transcribe")

# `/chat/stream` es la única ruta que cuesta dinero, y en la superficie pública
# no la protege nada más: autenticar no sirve ahí porque el bearer vive en el
# navegador de una máquina donde cualquiera se sienta. Ver `cuota.py`.
_CUOTA = cuota_publica()


_BITACORA = Bitacora()


async def _pregunta_de(request: Request) -> str | None:
    """El texto del turno, para la bitácora.

    Leer el cuerpo aquí es seguro: Starlette lo cachea en la primera lectura,
    así que el endpoint lo vuelve a recibir entero. Si viene mal formado no es
    asunto de la puerta — la validación de FastAPI ya lo rechazará después.
    """
    try:
        cuerpo = await request.json()
    except Exception:  # noqa: BLE001
        return None
    if isinstance(cuerpo, dict):
        valor = cuerpo.get("message") or cuerpo.get("text")
        return valor if isinstance(valor, str) else None
    return None


async def _puerta(
    request: Request,
    x_fenix_admin: str | None = Header(default=None),
    x_fenix_acceso: str | None = Header(default=None),
    x_forwarded_for: str | None = Header(default=None),
) -> None:
    """Qué puede tocar quien llama, cuánto puede gastar, y que quede escrito."""
    ruta = request.url.path
    admin = es_admin(x_fenix_admin)

    # El historial de la papelería lleva nombre del alumno, escuela y el
    # WhatsApp de la mamá. 404 y no 403: para una PC del cibercafé esa
    # superficie no existe; un 403 confirmaría que hay algo detrás.
    if ruta.startswith(_RUTAS_DEL_MOSTRADOR) and not admin:
        raise HTTPException(status_code=404, detail="no encontrado")

    # El mostrador no se limita: cotizar una lista de treinta artículos son
    # muchos turnos seguidos, y frenar una venta a media captura cuesta más que
    # lo que esto previene.
    if ruta != "/chat/stream" or admin:
        return

    clave = clave_de(request.client.host if request.client else None, x_forwarded_for)

    # La contraseña va ANTES de la cuota: a un escáner de internet no se le
    # regala un turno de modelo por descubrir la URL, y sus intentos fallidos
    # tampoco deben gastar el presupuesto del niño que sí la tiene.
    if hay_contrasena() and not acceso_valido(x_fenix_acceso):
        _BITACORA.anotar(ip=clave, rol="desconocido", cortado=True, extra={"motivo": "sin_contrasena"})
        raise HTTPException(
            status_code=401,
            detail={
                "code": "ACCESO_REQUERIDO",
                "message": "Escribe la contraseña de la papelería para usar el asistente.",
            },
        )

    try:
        _CUOTA.consumir(clave)
    except CuotaAgotada as agotada:
        # 429 con el tiempo real de espera, no un 500 ni un silencio: el
        # niño tiene que entender que le toca esperar, no creer que se
        # descompuso.
        _BITACORA.anotar(ip=clave, rol="publico", cortado=True, extra={"motivo": "cuota"})
        raise HTTPException(
            status_code=429,
            detail={
                "code": "CUOTA_AGOTADA",
                "message": "Ya usaste muchas preguntas seguidas. Espera un momento y sigue.",
                "retry_after": agotada.segundos,
            },
            headers={"Retry-After": str(agotada.segundos)},
        ) from agotada

    _BITACORA.anotar(ip=clave, rol="publico", texto=await _pregunta_de(request))


# Instancia PROPIA de og118, con la puerta puesta desde el constructor. La
# dependencia es por-app: og118 nunca la ve.
app = create_app(dependencies=[Depends(_puerta)])

app.include_router(router)


# --- Quién contesta según desde dónde preguntan ------------------------------
#
# El mismo servidor atiende dos productos. La persona de la papelería tiene
# prohibido internet y sólo cotiza de la lista maestra — correcto en el
# mostrador, inservible en el cibercafé: verificado en runtime, ante "¿quién
# ganó el Mundial de 2022?" contesta "esa pregunta no es de mi cancha".
#
# El criterio es quién llama, no un token que el cliente elija: si la persona
# dependiera de un campo del request, cualquiera pediría la del mostrador.
TUTOR_PATH = Path(__file__).parent / "prompts" / "tutor.md"

_runner_tutor = None
# `_selector_por_rol` es una dependencia SÍNCRONA, así que FastAPI la corre en un
# threadpool: dos primeras peticiones entran de verdad en paralelo y construían
# dos runners. El candado no protege datos, evita el trabajo duplicado.
_candado_tutor = threading.Lock()


def _tutor():
    """El runner del cibercafé: otra persona Y otro cinturón de herramientas.

    Cambiar sólo la persona no acotaba NADA. Con las capabilities de og118, este
    runner heredaba `rag_store` —search, ingest, delete_document, delete_corpus—
    y el MCP de expedientes, todo apuntando al negocio. Comprobado en runtime:
    una petición SIN ninguna credencial llamó `search_documents` y devolvió
    precios textuales de la lista maestra. Con las destructivas presentes, un
    `delete_corpus` desde una PC del ciber se lleva el activo del que depende
    cotizar.

    `task_tracker` se queda: es el plan/steps del glass-box, en memoria y sin
    alcance a datos. Lo que se va es todo lo que toca el negocio.

    Perezoso porque la mayoría de los arranques son del mostrador. `load_prompt`
    relee por mtime, así que editar `tutor.md` aplica sin reiniciar.
    """
    global _runner_tutor
    if _runner_tutor is None:
        with _candado_tutor:
            if _runner_tutor is None:
                _runner_tutor = build_runner(
                    persona_text=load_prompt(TUTOR_PATH),
                    capabilities=["task_tracker"],
                    extra_mcp_servers=[],
                )
    return _runner_tutor


def _selector_por_rol(
    x_fenix_admin: str | None = Header(default=None),
):
    base = get_runner_selector()
    if es_admin(x_fenix_admin):
        return base

    def _publico(_token: str | None):
        # El elemento se ignora a propósito: es el selector de persona de og118,
        # y dejarlo vivo aquí sería la puerta trasera que este selector cierra.
        return _tutor(), None

    return _publico


app.dependency_overrides[get_runner_selector] = _selector_por_rol
