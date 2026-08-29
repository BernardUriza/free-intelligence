"""La cobertura de Proyectos con la feature ENCENDIDA.

Proyectos vive apagado por default desde el 2026-08-29 (`OG118_PROYECTOS`, ver
`app.proyectos_activos`). Estas suites son las que ejercen la rama viva.

**Por qué no se borraron cuando la feature se apagó:** una rama apagada sin
tests es código que se pudre en silencio y que descubres roto el día que lo
prendes. El bug del corpus del 2026-08-29 —la subida escribiendo en un HDF5 que
la búsqueda ya no leía— existió exactamente así: un `else` que nadie corría. El
trato al esconder Proyectos en vez de borrarlo fue que su rama quedara cubierta;
esta carpeta es ese trato.

**Sin `importlib.reload`, a propósito.** La primera versión recargaba `app` y
`runner` para que vieran el flag; recargar un módulo compartido en una sesión de
pytest le derrama estado a las suites que corren después, y contaminó siete
tests ajenos. La cura fue leer el flag AL LLAMAR (`proyectos_activos()`), que es
lo que permite construir una app encendida por la costura que ya existía —
`create_app()`— sin tocar el módulo de nadie.

`test_projects_flag.py` (fuera de aquí) afirma el interruptor en las dos
posiciones. Estas suites afirman lo que hay del lado encendido.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest


@pytest.fixture(autouse=True)
def _proyectos_encendidos(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Enciende el flag y monta el `projects_router` en la app compartida.

    MONTA en vez de sustituir, y la diferencia importa: el conftest raíz corre
    ANTES que éste (pytest ordena las fixtures autouse de conftest más alto
    primero) y deja sus `dependency_overrides` en la instancia que ya existe.
    Cambiar `app.app` por una nueva tiraba esos overrides al piso y rompía veinte
    tests de esta misma carpeta.

    La lista de rutas se restaura al salir, así que ninguna suite posterior
    hereda `/projects` montado.
    """
    import app as app_module

    monkeypatch.setenv("OG118_PROYECTOS", "1")
    rutas_previas = list(app_module.app.router.routes)
    app_module.app.include_router(app_module.projects_router)
    yield
    app_module.app.router.routes[:] = rutas_previas
