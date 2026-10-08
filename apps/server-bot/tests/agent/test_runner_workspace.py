"""Runner workspace window — authenticated read-only views of the agents' persistent
workspace (`GET /v1/workspace`, `GET /v1/workspace/file`). The first slice of the
"log in and see what the agents build" dream: it must require auth, skip VCS/cache
noise, and NEVER read outside WORKSPACE_ROOT (path-traversal safe).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import persona_runner.runner as runner
from persona_runner.core import config as runner_config


@pytest.fixture
def client(tmp_path, monkeypatch):
    (tmp_path / "notes.md").write_text("hola mundo", encoding="utf-8")
    sub = tmp_path / "sub"
    sub.mkdir()
    (sub / "data.txt").write_text("nested", encoding="utf-8")
    gitdir = tmp_path / ".git"
    gitdir.mkdir()
    (gitdir / "config").write_text("skip me", encoding="utf-8")
    monkeypatch.setattr(runner_config, "WORKSPACE_ROOT", tmp_path)
    monkeypatch.setattr(runner_config, "RUNNER_AUTH_TOKEN", "secret")
    return TestClient(runner.app)


def test_workspace_list_requires_auth(client):
    assert client.get("/v1/workspace").status_code == 401


def test_workspace_list_returns_files_skipping_vcs_noise(client):
    r = client.get("/v1/workspace", headers={"Authorization": "Bearer secret"})
    assert r.status_code == 200
    paths = {f["path"] for f in r.json()["files"]}
    assert "notes.md" in paths
    assert "sub/data.txt" in paths
    assert not any(".git" in p for p in paths)


def test_los_paths_van_en_posix_los_sirva_quien_los_sirva(client):
    r"""El separador del JSON no puede depender del SO donde corre el runner.

    `str(Path("sub/data.txt"))` da `sub\data.txt` en Windows y `sub/data.txt`
    en Linux, así que con `str()` la MISMA API contesta distinto según dónde se
    hospeda. En producción el runner corre en Linux y el defecto es invisible;
    aparece en cuanto alguien levanta la suite en Windows — que es como se
    encontró (2026-09-08).
    """
    r = client.get("/v1/workspace", headers={"Authorization": "Bearer secret"})
    paths = [f["path"] for f in r.json()["files"]]
    assert paths, "sin archivos no se prueba nada"
    culpables = [p for p in paths if "\\" in p]
    assert not culpables, f"paths con separador de Windows en la respuesta: {culpables}"


def test_el_path_que_devuelve_la_lista_sirve_para_pedir_el_archivo(client):
    """El viaje redondo, que es el contrato real y no lo probaba nadie.

    `/v1/workspace` devuelve un `path` por archivo y el cliente lo manda tal
    cual a `/v1/workspace/file?path=`. Si el formato de ida no sirve de vuelta,
    la única forma de usar la API es que el cliente adivine el SO del servidor.
    Se prueba con el archivo ANIDADO a propósito: uno en la raíz no tiene
    separador y pasaría aunque el defecto siguiera vivo.
    """
    listado = client.get("/v1/workspace", headers={"Authorization": "Bearer secret"})
    anidado = next(f["path"] for f in listado.json()["files"] if "/" in f["path"] or "\\" in f["path"])

    r = client.get(
        "/v1/workspace/file",
        params={"path": anidado},
        headers={"Authorization": "Bearer secret"},
    )
    assert r.status_code == 200, f"la lista dio {anidado!r} y /file no lo pudo leer"
    assert r.json()["content"] == "nested"


def test_workspace_file_reads_content(client):
    r = client.get(
        "/v1/workspace/file",
        params={"path": "notes.md"},
        headers={"Authorization": "Bearer secret"},
    )
    assert r.status_code == 200
    assert r.json()["content"] == "hola mundo"


def test_workspace_file_requires_auth(client):
    assert client.get("/v1/workspace/file", params={"path": "notes.md"}).status_code == 401


def test_workspace_file_rejects_path_traversal(client):
    r = client.get(
        "/v1/workspace/file",
        params={"path": "../../etc/passwd"},
        headers={"Authorization": "Bearer secret"},
    )
    assert r.status_code == 400


def test_workspace_file_404_when_missing(client):
    r = client.get(
        "/v1/workspace/file",
        params={"path": "nope.md"},
        headers={"Authorization": "Bearer secret"},
    )
    assert r.status_code == 404


def test_add_rule_requires_auth(client):
    assert client.post("/v1/workspace/rule", json={"rule": "sé breve"}).status_code == 401


def test_add_rule_appends_and_is_readable(client, tmp_path):
    h = {"Authorization": "Bearer secret"}
    assert client.post("/v1/workspace/rule", json={"rule": "sé más breve"}, headers=h).status_code == 200
    assert client.post("/v1/workspace/rule", json={"rule": "usa más ejemplos"}, headers=h).status_code == 200
    claude_md = (tmp_path / "CLAUDE.md").read_text(encoding="utf-8")
    # append-only: BOTH rules survive, under the marked section
    assert "House Rules" in claude_md
    assert "sé más breve" in claude_md
    assert "usa más ejemplos" in claude_md


def test_add_rule_rejects_empty(client):
    r = client.post("/v1/workspace/rule", json={"rule": "   "}, headers={"Authorization": "Bearer secret"})
    assert r.status_code == 400
