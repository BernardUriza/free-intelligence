"""La puerta del mostrador sobre las rutas que Fénix hereda de og118.

og118 sirve `/conversations` y `/projects` abiertas: es una app de una sola
cuenta. En la papelería no puede serlo — el título de cada conversación lleva el
nombre del alumno, su escuela y el WhatsApp de la mamá, y las PCs del cibercafé
llegan al mismo servidor.

Estos tests existen porque la puerta se pone MUTANDO rutas ajenas: si og118
renombra `/conversations`, el filtro deja de encontrarlas y el hueco se reabre
sin que nada falle. Aquí falla.
"""

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
    """El default de desarrollo, explícito para que nadie lo despliegue así."""
    monkeypatch.delenv("FENIX_ADMIN_TOKEN", raising=False)
    c = _cliente(app_fenix)
    datos = c.get("/expedientes/rol").json()
    assert datos["admin"] is True
    assert datos["modoAbierto"] is True


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


def test_la_persona_del_tutor_existe_y_permite_buscar(app_fenix):
    """El caso de uso de Bernard —investigar el resultado de un evento— muere si
    esta persona hereda el "no busques en internet" de la papelería."""
    import fenix_app

    texto = fenix_app.TUTOR_PATH.read_text(encoding="utf-8").lower()
    assert "internet" in texto
    assert "no pidas datos personales" in texto


def test_se_cerro_alguna_ruta_heredada(app_fenix):
    """El guardia contra el silencio: si og118 mueve sus rutas, esto lo grita."""
    import fenix_app

    assert "/conversations" in fenix_app._CERRADAS
    assert "/projects" in fenix_app._CERRADAS
