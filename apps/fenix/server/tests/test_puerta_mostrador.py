"""La puerta del mostrador sobre las rutas que Fénix hereda de og118.

og118 sirve `/conversations` y `/projects` abiertas: es una app de una sola
cuenta. En la papelería no puede serlo — el título de cada conversación lleva el
nombre del alumno, su escuela y el WhatsApp de la mamá, y las PCs del cibercafé
llegan al mismo servidor.

Estos tests existen porque la puerta se pone MUTANDO rutas ajenas: si og118
renombra `/conversations`, el filtro deja de encontrarlas y el hueco se reabre
sin que nada falle. Aquí falla.
"""

import pytest
from fastapi.testclient import TestClient


def _cliente(app):
    return TestClient(app)


ADMIN = {"X-Fenix-Admin": "token-de-prueba"}


def test_las_rutas_heredadas_no_responden_sin_token(app_fenix):
    c = _cliente(app_fenix)
    for ruta in ("/conversations", "/projects"):
        r = c.get(ruta)
        assert r.status_code == 404, f"{ruta} quedó abierta: {r.status_code}"


def test_las_rutas_heredadas_responden_con_el_token(app_fenix):
    c = _cliente(app_fenix)
    for ruta in ("/conversations", "/projects"):
        assert c.get(ruta, headers=ADMIN).status_code == 200


def test_un_token_equivocado_es_indistinguible_de_no_tener_ninguno(app_fenix):
    # 404 y no 403: para la PC del cibercafé la superficie no existe. Un 403
    # confirmaría que hay algo detrás que vale la pena adivinar.
    c = _cliente(app_fenix)
    assert c.get("/conversations", headers={"X-Fenix-Admin": "otro"}).status_code == 404


def test_el_chat_publico_sigue_abierto(app_fenix):
    """Cerrar de más rompería el cibercafé, que es la mitad del producto."""
    c = _cliente(app_fenix)
    assert c.get("/health").status_code == 200
    assert c.get("/expedientes/rol").status_code == 200


def test_el_rol_distingue_mostrador_de_publico(app_fenix):
    c = _cliente(app_fenix)
    assert c.get("/expedientes/rol").json()["admin"] is False
    assert c.get("/expedientes/rol", headers=ADMIN).json()["admin"] is True


def test_sin_token_configurado_todo_es_mostrador(app_fenix, monkeypatch):
    """El modo abierto sigue existiendo — pero hay que pedirlo (ver abajo)."""
    monkeypatch.delenv("FENIX_ADMIN_TOKEN", raising=False)
    c = _cliente(app_fenix)
    datos = c.get("/expedientes/rol").json()
    assert datos["admin"] is True
    assert datos["modoAbierto"] is True


def test_el_arranque_se_niega_a_dejar_el_negocio_abierto_por_descuido(monkeypatch):
    """Un warning en un log no es un guardia.

    Un deploy que olvidara `FENIX_ADMIN_TOKEN` servía la lista completa de
    expedientes —alumnos, escuelas, WhatsApps de las mamás— y se veía igual que
    uno correcto: arrancaba bien y nadie lee la salida de un contenedor sano.
    """
    from rbac import ConfiguracionInsegura, exigir_config

    monkeypatch.delenv("FENIX_ADMIN_TOKEN", raising=False)
    monkeypatch.delenv("FENIX_MODO_ABIERTO", raising=False)
    with pytest.raises(ConfiguracionInsegura):
        exigir_config()


def test_el_modo_abierto_se_alcanza_tecleandolo(monkeypatch):
    """Un estado inseguro por omisión es un accidente; declarado, una decisión."""
    from rbac import exigir_config

    monkeypatch.delenv("FENIX_ADMIN_TOKEN", raising=False)
    monkeypatch.setenv("FENIX_MODO_ABIERTO", "1")
    exigir_config()

    monkeypatch.setenv("FENIX_ADMIN_TOKEN", "algo")
    monkeypatch.delenv("FENIX_MODO_ABIERTO", raising=False)
    exigir_config()


def test_el_cibercafe_habla_con_el_tutor_y_el_mostrador_con_la_papeleria(app_fenix):
    """Dos productos, un servidor. La persona la decide quién llama.

    La de la papelería tiene prohibido internet y sólo cotiza de la lista
    maestra: en el cibercafé contestaba "esa pregunta no es de mi cancha" a
    cualquier duda de tarea.
    """
    import fenix_app

    publico = fenix_app._selector_por_rol(x_fenix_admin=None)
    mostrador = fenix_app._selector_por_rol(x_fenix_admin="token-de-prueba")

    runner_publico, elemento = publico(None)
    assert elemento is None
    assert runner_publico is fenix_app._tutor()
    assert mostrador(None)[0] is not runner_publico


def test_el_cibercafe_no_puede_pedir_la_persona_del_mostrador(app_fenix):
    """El elemento es el selector de persona de og118; aquí sería la puerta
    trasera que este selector existe para cerrar."""
    import fenix_app

    publico = fenix_app._selector_por_rol(x_fenix_admin=None)
    for intento in (None, "", "oxigeno", "53", "papeleria"):
        assert publico(intento)[0] is fenix_app._tutor()


def test_el_runner_publico_no_alcanza_los_datos_del_negocio(app_fenix):
    """La persona decide lo que el modelo QUIERE; las capabilities lo que PUEDE.

    Comprobado en runtime antes de este arreglo: una petición SIN ninguna
    credencial llamó `mcp__fi-core-rag-store__search_documents` y devolvió
    precios textuales de la lista maestra. El mismo cinturón traía
    `delete_corpus` —que se lleva el activo del que depende cotizar— y el MCP
    de expedientes, que escribe fichas de clientes sin verificar nada.
    """
    import fenix_app

    tutor = fenix_app._tutor()
    herramientas = " ".join(str(s) for s in (tutor.capabilities or []))
    assert "rag_store" not in herramientas
    assert not (tutor.extra_mcp_servers or []), "el tutor no lleva el MCP de expedientes"

    # El del mostrador SÍ los necesita: sin rag_store no puede leer la lista
    # maestra, que es su trabajo entero.
    from app import _runner

    assert "rag_store" in " ".join(str(s) for s in (_runner.capabilities or []))


def test_la_persona_del_tutor_existe_y_permite_buscar(app_fenix):
    """El caso de uso de Bernard —investigar el resultado de un evento— muere si
    esta persona hereda el "no busques en internet" de la papelería."""
    import fenix_app

    texto = fenix_app.TUTOR_PATH.read_text(encoding="utf-8").lower()
    assert "internet" in texto
    assert "no pidas datos personales" in texto


def test_endurecer_fenix_no_toca_la_app_de_og118(app_fenix):
    """Las dos apps, vivas en el mismo proceso, con puertas distintas.

    Cuando Fénix mutaba el objeto `app` compartido, su cierre viajaba de vuelta:
    con FENIX_ADMIN_TOKEN en el entorno, 12 tests de og118 fallaban con 404 en
    rutas que og118 sirve abiertas a propósito. Aquí se afirma lo contrario.
    """
    import app as og118

    assert _cliente(app_fenix).get("/conversations").status_code == 404
    assert _cliente(og118.app).get("/conversations").status_code == 200
    assert app_fenix is not og118.app
    assert og118.get_runner_selector not in og118.app.dependency_overrides


class _RunnerFalso:
    """Un turno que no llama al modelo.

    Sin esto, probar la cuota gastaría cuota real y tardaría minutos — el
    absurdo exacto que estos tests existen para prevenir.
    """

    async def run_stream(self, *_a, **_k):
        yield {"type": "result", "result": {"text": "ok"}}
        yield {"type": "done"}


@pytest.fixture
def sin_modelo(app_fenix):
    """Cablea el runner falso en la app, respetando el turno real de la cuota."""
    import app as og118

    app_fenix.dependency_overrides[og118.get_runner_selector] = lambda: (
        lambda _token: (_RunnerFalso(), None)
    )
    yield app_fenix
    app_fenix.dependency_overrides.pop(og118.get_runner_selector, None)


def test_el_publico_agota_su_cuota_de_turnos(sin_modelo, monkeypatch):
    """`/chat/stream` es el único endpoint que cuesta dinero y no lo protegía nada.

    Se ejercita la RUTA real, no la clase: un límite que existe pero no está
    cableado al endpoint es exactamente el fake-green que esto previene.
    """
    import fenix_app

    monkeypatch.setattr(fenix_app, "_CUOTA", fenix_app.cuota_publica())
    fenix_app._CUOTA.por_minuto = 2
    c = _cliente(sin_modelo)

    cuerpo = {"message": "hola"}
    codigos = [c.post("/chat/stream", json=cuerpo).status_code for _ in range(3)]
    assert codigos[-1] == 429, f"el tercer turno público debió cortarse: {codigos}"

    respuesta = c.post("/chat/stream", json=cuerpo)
    assert respuesta.headers.get("Retry-After")
    assert respuesta.json()["detail"]["code"] == "CUOTA_AGOTADA"


def test_al_mostrador_no_se_le_corta_una_venta(sin_modelo, monkeypatch):
    """Cotizar treinta artículos son muchos turnos seguidos; frenar eso cuesta
    más que lo que la cuota previene."""
    import fenix_app

    monkeypatch.setattr(fenix_app, "_CUOTA", fenix_app.cuota_publica())
    fenix_app._CUOTA.por_minuto = 1
    c = _cliente(sin_modelo)

    for _ in range(5):
        r = c.post("/chat/stream", json={"message": "hola"}, headers=ADMIN)
        assert r.status_code != 429


def test_se_puso_cuota_en_la_ruta_que_cuesta(app_fenix):
    """Si og118 mueve /chat/stream, el gasto se queda sin techo en silencio."""
    import fenix_app

    assert "/chat/stream" in fenix_app._CON_CUOTA


def test_se_cerro_alguna_ruta_heredada(app_fenix):
    """El guardia contra el silencio: si og118 mueve sus rutas, esto lo grita."""
    import fenix_app

    assert "/conversations" in fenix_app._CERRADAS
    assert "/projects" in fenix_app._CERRADAS
