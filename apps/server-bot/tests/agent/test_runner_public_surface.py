"""La superficie que el runner le ofrece a un desconocido.

`persona-runner` es la ÚNICA app del environment con ingress externo, y tiene que
serlo: un humano abre los artifacts (`GET /a/{id}`) en su navegador y AIRE llama
`/mcp/{casita}` desde el droplet, fuera de Azure. Eso significa que todo lo que el
proceso publique sin auth queda publicado en internet abierto.

Medido el 2026-09-09 contra el FQDN público, con la revisión de ese día:

    /docs           200
    /openapi.json   200

O sea el mapa completo de la API —turno, judge, workspace, MCP— con sus esquemas,
servido a quien encuentre el FQDN. No es una brecha: `core/auth.py` es fail-closed
y compara en tiempo constante, así que ningún endpoint responde sin token. Es
reconocimiento gratis, y no compra nada a cambio.

Este archivo fija que la puerta quede cerrada por default y que cerrarla no haya
apagado de paso lo que SÍ tiene que ser público.
"""

from __future__ import annotations

import importlib

import pytest
from fastapi.testclient import TestClient

import persona_runner.runner as runner
from persona_runner.core import config as runner_config

DOCS_SIN_AUTH = ["/docs", "/redoc", "/openapi.json"]


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(runner_config, "WORKSPACE_ROOT", tmp_path)
    monkeypatch.setattr(runner_config, "RUNNER_AUTH_TOKEN", "secret")
    return TestClient(runner.app)


@pytest.mark.parametrize("ruta", DOCS_SIN_AUTH)
def test_la_documentacion_interactiva_no_se_publica(client, ruta):
    """FastAPI las sirve sin auth por default; acá van apagadas."""
    assert client.get(ruta).status_code == 404, (
        f"{ruta} volvió a quedar pública. En este runner eso es internet abierto, "
        "no la red interna — ver config.DOCS_ENABLED."
    )


def test_health_sigue_siendo_publico(client):
    """RESISTENCIA: apagar los docs no puede apagar la sonda de salud.

    `/health` es deliberadamente anónimo — la plataforma lo consulta sin
    credencial, y un 404 acá haría que la revisión nunca se declare sana.
    """
    assert client.get("/health").status_code == 200


def test_los_endpoints_siguen_exigiendo_token(client):
    """RESISTENCIA: el valor de este cambio es esconder el mapa, NO sustituir la
    autenticación. Si alguien lee esto como 'ya no hace falta el bearer', esto
    truena."""
    assert client.get("/v1/workspace").status_code == 401


def test_se_pueden_encender_a_proposito_para_desarrollo_local(monkeypatch, tmp_path):
    """La puerta es opt-in, no una pared: en local los docs son útiles.

    Se reconstruye la app con el flag encendido, porque `docs_url` se resuelve al
    construir `FastAPI(...)` y no en cada request.
    """
    monkeypatch.setenv("RUNNER_DOCS_ENABLED", "1")
    cfg = importlib.reload(runner_config)
    assert cfg.DOCS_ENABLED is True

    recargado = importlib.reload(runner)
    monkeypatch.setattr(recargado.config, "WORKSPACE_ROOT", tmp_path)
    monkeypatch.setattr(recargado.config, "RUNNER_AUTH_TOKEN", "secret")
    # Sin `with`: el lifespan verifica la ruta de AIRE contra el env real y aquí
    # no hay gate. Lo que se prueba es el ruteo, no el arranque.
    assert TestClient(recargado.app).get("/openapi.json").status_code == 200

    # Dejar los módulos como estaban para no contaminar el resto de la suite.
    monkeypatch.delenv("RUNNER_DOCS_ENABLED", raising=False)
    importlib.reload(runner_config)
    importlib.reload(runner)
