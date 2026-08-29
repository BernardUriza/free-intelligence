"""OG118_PROYECTOS — la feature de Proyectos, apagada por default, viva con el flag.

Bernard dejó de usar Proyectos el 2026-08-29 y pidió esconderla en vez de
borrarla, para retomarla después. Este archivo es la condición que hace que eso
NO se pudra, y existe por un precedente muy concreto:

El bug del corpus del 2026-08-29 —la subida escribiendo en un HDF5 que la
búsqueda ya no leía— existió porque `get_rag_store()` tenía un
`if OG118_BACKEND == "aire"` con un `else` que nadie corría. Una rama apagada sin
test es esa misma trampa esperando a que alguien la prenda. Así que aquí se
afirman LAS DOS: la apagada (que es la que corre en producción) y la prendida
(que es la que Bernard va a encontrarse el día que vuelva).

El flag se lee AL LLAMAR (`proyectos_activos()`), no al importar, así que cada
rama se construye por la costura que ya existía —`create_app()`— sin recargar
módulos. Esa decisión no es estética: la primera versión de este archivo usaba
`importlib.reload`, y una recarga de `app` en una sesión de pytest le derramó
estado a siete tests de otras suites.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def apagado(monkeypatch: pytest.MonkeyPatch) -> Iterator[object]:
    """og118 como corre en producción."""
    import app as app_module

    monkeypatch.delenv("OG118_PROYECTOS", raising=False)
    monkeypatch.setattr(app_module, "app", app_module.create_app())
    yield app_module


@pytest.fixture
def encendido(monkeypatch: pytest.MonkeyPatch) -> Iterator[object]:
    """og118 el día que Bernard retome Proyectos."""
    import app as app_module

    monkeypatch.setenv("OG118_PROYECTOS", "1")
    monkeypatch.setattr(app_module, "app", app_module.create_app())
    yield app_module


# --- la rama APAGADA: la que corre en producción -----------------------------


def test_apagado_por_default(monkeypatch) -> None:
    """Sin la variable, apagado. Un default que hay que declarar para apagar es
    un default encendido con disfraz."""
    import app as app_module

    monkeypatch.delenv("OG118_PROYECTOS", raising=False)
    assert app_module.proyectos_activos() is False


def test_apagado_las_rutas_NO_EXISTEN(apagado) -> None:
    """404 real, no un handler que consulta un flag: el `projects_router` no se
    monta, así que no hay ruta que responder."""
    rutas = {r.path for r in apagado.app.routes}
    assert not any(p.startswith("/projects") for p in rutas), sorted(rutas)
    c = TestClient(apagado.app)
    for ruta in ("/projects", "/projects/x", "/projects/x/documents"):
        assert c.get(ruta).status_code == 404


def test_apagado_el_runner_no_pide_rag_store(apagado) -> None:
    """Y por lo tanto `delete_corpus` no es alcanzable por el modelo: la tool que
    lo trae no viaja en el turno."""
    import runner as runner_module

    assert "rag_store" not in runner_module.capacidades_por_defecto()
    assert runner_module.build_runner().backend.registry_tools == ("persona", "task_tracker")


def test_apagado_no_ata_contexto_al_turno(apagado) -> None:
    """Sin corpus ni workspace, un addendum le prometería al modelo un contexto
    que el turno nunca trae."""
    import runner as runner_module

    assert runner_module.build_runner().context_prompt is None


def test_apagado_un_corpus_id_viejo_NO_rompe_el_chat(apagado) -> None:
    """Una pestaña sin recargar sigue mandando `corpus_id`. Se IGNORA, no se
    rechaza: romperle el chat entero por una feature que él no pidió sería
    cambiar una molestia por una caída."""
    campos = apagado.ChatRequest.model_fields
    assert "corpus_id" in campos, "el campo sigue aceptándose para no 422-ear a un cliente viejo"
    req = apagado.ChatRequest(message="hola", corpus_id="project-de-ayer")
    assert req.corpus_id == "project-de-ayer"


# --- la rama ENCENDIDA: la que Bernard se va a encontrar el día que vuelva ----


def test_encendido_las_rutas_se_montan(encendido) -> None:
    rutas = {r.path for r in encendido.app.routes}
    for esperada in ("/projects", "/projects/{project_id}", "/projects/{project_id}/documents"):
        assert esperada in rutas, sorted(p for p in rutas if "project" in p)


def test_encendido_el_runner_recupera_rag_store(encendido) -> None:
    import runner as runner_module

    assert "rag_store" in runner_module.capacidades_por_defecto()
    assert "rag_store" in runner_module.build_runner().backend.registry_tools


def test_encendido_ata_el_contexto_del_turno(encendido) -> None:
    """El binding vuelve: uno dice DÓNDE buscar, el otro CÓMO contestar."""
    import runner as runner_module

    assert runner_module.build_runner().context_prompt is not None


def test_encendido_un_consumer_que_pide_menos_sigue_acotado(encendido) -> None:
    """El flag enciende la feature, no relaja el acotamiento: el tutor del
    cibercafé de fenix pide una tool y recibe una."""
    import runner as runner_module

    tutor = runner_module.build_runner(persona_text="tutor", capabilities=["task_tracker"])
    assert tutor.backend.registry_tools == ("task_tracker",)
