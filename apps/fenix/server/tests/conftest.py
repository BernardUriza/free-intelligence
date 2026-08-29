"""Cableado de tests para el servidor de Fénix.

Fénix no es un servidor propio: monta su router sobre la app de og118. Por eso
el path lleva PRIMERO el directorio de fenix y luego el de og118 — el mismo
orden que usa `uvicorn --app-dir`, y lo que hace que `import fenix_app` gane
sobre el `app.py` de og118.
"""

import sys
from pathlib import Path

import pytest

FENIX = Path(__file__).resolve().parent.parent
OG118 = FENIX.parents[1] / "og118" / "server"
for ruta in (str(OG118), str(FENIX)):
    if ruta not in sys.path:
        sys.path.insert(0, ruta)


@pytest.fixture
def app_fenix(tmp_path, monkeypatch):
    """La app con un token de mostrador conocido y datos en un tmp.

    El token se fija ANTES de importar: `rbac` lo lee del entorno en cada
    llamada, pero los expedientes se guardan donde diga la variable al construir
    el store, y ningún test debe escribir en los datos reales de la papelería.
    """
    monkeypatch.setenv("FENIX_ADMIN_TOKEN", "token-de-prueba")
    # Los tests no atienden a nadie: se declara uso personal para que la
    # invariante de ToS no bloquee el import.
    monkeypatch.setenv("FENIX_USO_PERSONAL", "1")
    # Ídem con la contraseña del tutor: sin declarar el modo abierto (lo que
    # dev.sh sí declara), la invariante de e3c295ae reventaba el import de
    # fenix_app y con él la suite entera — 24 errors que no probaban nada.
    monkeypatch.setenv("FENIX_TUTOR_ABIERTO", "1")
    # El motor del turno no se hereda del entorno de quien corre los tests: la
    # app del fixture siempre nace en la ruta byte-idéntica de siempre.
    for var in ("FENIX_AIRE_PROJECT", "OG118_AIRE_PROJECT"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("FENIX_EXPEDIENTES_PATH", str(tmp_path / "expedientes.json"))
    monkeypatch.setenv("OG118_PROJECT_REGISTRY_PATH", str(tmp_path / "projects.json"))
    monkeypatch.setenv("OG118_CONVERSATIONS_PATH", str(tmp_path / "conversations"))

    import fenix_app

    fenix_app._store = None
    return fenix_app.app
