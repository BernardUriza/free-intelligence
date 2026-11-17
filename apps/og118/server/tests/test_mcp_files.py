"""The `files` remote MCP: the model saves, lists and reads the account's files by capsule."""

from __future__ import annotations

import base64
import dataclasses
import time

import pytest
from fastapi.testclient import TestClient

import app as app_module
from background_jobs import sign_capsule, verify_capsule

SECRET = "s3cret-de-prueba"
H5_MAGIC = b"\x89HDF\r\n\x1a\n" + bytes(range(64))


@pytest.fixture
def client(monkeypatch) -> TestClient:
    monkeypatch.setenv("OG118_MCP_TOKEN", SECRET)
    return TestClient(app_module.app)


def _capsule(sub: str = "acct-A", cid: str = "conv-1", **kw) -> str:
    return sign_capsule(SECRET, sub=sub, conversation_id=cid, corpus_id=None, **kw)


def _rpc(client, capsule, method, params=None):
    return client.post(
        f"/mcp/files/{capsule}",
        json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}},
    )


def _call(client, capsule, tool, /, **arguments) -> dict:
    return _rpc(client, capsule, "tools/call", {"name": tool, "arguments": arguments}).json()["result"]


def test_a_capsule_we_did_not_sign_finds_no_door(client):
    forged = sign_capsule("otro-secreto", sub="acct-A", conversation_id="conv-1", corpus_id=None)
    assert _rpc(client, forged, "tools/list").status_code == 404
    assert _rpc(client, "basura", "tools/call", {"name": "list_files"}).status_code == 404


def test_without_the_secret_the_door_does_not_exist(client, monkeypatch):
    capsule = _capsule()
    monkeypatch.delenv("OG118_MCP_TOKEN")
    assert _rpc(client, capsule, "tools/list").status_code == 404


def test_the_surface_is_three_tools_and_none_deletes(client):
    tools = _rpc(client, _capsule(), "tools/list").json()["result"]["tools"]
    assert [t["name"] for t in tools] == ["save_file", "list_files", "read_file"]


def test_a_text_file_saved_by_the_model_is_downloadable_by_its_owner(client, as_account):
    res = _call(client, _capsule(), "save_file", name="notas.md", content="# hola\nñandú")
    assert res["isError"] is False

    listing = client.get("/files", params={"conversationId": "conv-1"}).json()["files"]
    assert [f["name"] for f in listing] == ["notas.md"]
    got = client.get(f"/files/{listing[0]['id']}")
    assert got.content == "# hola\nñandú".encode("utf-8")
    assert got.headers["content-type"].startswith("text/plain")


def test_base64_keeps_binary_bytes_identical(client, as_account):
    res = _call(
        client, _capsule(), "save_file",
        name="datos.h5", content=base64.b64encode(H5_MAGIC).decode(), encoding="base64",
        content_type="application/x-hdf5",
    )
    assert res["isError"] is False
    (meta,) = client.get("/files").json()["files"]
    assert client.get(f"/files/{meta['id']}").content == H5_MAGIC


def test_bad_base64_saves_nothing(client, file_store):
    res = _call(client, _capsule(), "save_file", name="x.bin", content="no es base64 !!", encoding="base64")
    assert res["isError"] is True
    assert file_store.list_for("acct-A") == []


def test_an_expired_capsule_saves_nothing(client, file_store):
    vencida = _capsule(now=time.time() - 7200)
    res = _call(client, vencida, "save_file", name="a.md", content="x")
    assert res["isError"] is True and "NOT saved" in res["content"][0]["text"]
    assert file_store.list_for("acct-A") == []


def test_the_caps_reach_the_model_as_an_error(client, file_store):
    res = _call(client, _capsule(), "save_file", name="gordo.txt", content="x" * 1025)
    assert res["isError"] is True and "limit" in res["content"][0]["text"]
    assert file_store.list_for("acct-A") == []


def test_list_is_scoped_to_the_conversation_unless_asked(client):
    _call(client, _capsule(cid="conv-1"), "save_file", name="uno.md", content="1")
    _call(client, _capsule(cid="conv-2"), "save_file", name="dos.md", content="2")

    aqui = _call(client, _capsule(cid="conv-1"), "list_files")["content"][0]["text"]
    assert "uno.md" in aqui and "dos.md" not in aqui
    todo = _call(client, _capsule(cid="conv-1"), "list_files", scope="account")["content"][0]["text"]
    assert "uno.md" in todo and "dos.md" in todo


def test_read_returns_text_and_withholds_binary(client, file_store):
    _call(client, _capsule(), "save_file", name="notas.md", content="contenido legible")
    _call(client, _capsule(), "save_file", name="d.h5", content=base64.b64encode(H5_MAGIC).decode(), encoding="base64")
    por_nombre = {f["name"]: f["id"] for f in file_store.list_for("acct-A")}

    assert _call(client, _capsule(), "read_file", id=por_nombre["notas.md"])["content"][0]["text"] == "contenido legible"
    binario = _call(client, _capsule(), "read_file", id=por_nombre["d.h5"])
    assert binario["isError"] is False and "not shown" in binario["content"][0]["text"]


def test_another_account_cannot_read_or_list(client, file_store):
    _call(client, _capsule(sub="acct-A"), "save_file", name="secreto.md", content="de A")
    (meta,) = file_store.list_for("acct-A")

    assert _call(client, _capsule(sub="acct-B"), "read_file", id=meta["id"])["isError"] is True
    assert _call(client, _capsule(sub="acct-B"), "list_files", scope="account")["content"][0]["text"] == "no files stored"


def test_without_infra_no_spec_and_no_promise(monkeypatch):
    for v in ("OG118_MCP_TOKEN", "OG118_PUBLIC_URL"):
        monkeypatch.delenv(v, raising=False)
    from runner import build_runner, files_tool_spec

    assert files_tool_spec("acct-A", "conv-1") == []
    assert "mcp__files__save_file" not in build_runner().persona


def test_with_infra_the_prompt_teaches_the_tool_and_the_spec_carries_the_identity(monkeypatch):
    monkeypatch.setenv("OG118_MCP_TOKEN", SECRET)
    monkeypatch.setenv("OG118_PUBLIC_URL", "https://api.example.org/")
    from runner import build_runner, files_tool_spec

    assert "mcp__files__save_file" in build_runner().persona
    assert "mcp__files__save_file" not in build_runner(files=False).persona
    (spec,) = files_tool_spec("acct-A", "conv-9")
    assert spec.is_http and spec.name == "files"
    identidad = verify_capsule(SECRET, spec.url.removeprefix("https://api.example.org/mcp/files/"))
    assert (identidad["sub"], identidad["cid"]) == ("acct-A", "conv-9")
    assert not spec.headers
    assert files_tool_spec("acct-A", None) == []


def test_the_chat_turn_mounts_the_files_door(monkeypatch):
    monkeypatch.setenv("OG118_MCP_TOKEN", SECRET)
    monkeypatch.setenv("OG118_PUBLIC_URL", "https://api.example.org")
    monkeypatch.delenv("OG118_JOB_RESOURCE_ID", raising=False)
    from fi_runner import Runner

    visto: dict = {}

    @dataclasses.dataclass
    class _Backend:
        registry_tools: tuple = ()

    class _Runner(Runner):
        async def run_stream(self, message, **kw):
            visto["extra"] = list(self.extra_mcp_servers)
            yield {"type": "result", "result": {"text": "ok"}}

    espia = _Runner(backend=_Backend(), persona="p")
    app_module.app.dependency_overrides[app_module.get_runner_selector] = lambda: (lambda element: (espia, None))
    try:
        with TestClient(app_module.app) as c:
            assert c.post("/chat/stream", json={"message": "hola", "session_id": "conv-7"}).status_code == 200
    finally:
        app_module.app.dependency_overrides.pop(app_module.get_runner_selector, None)
    (spec,) = visto["extra"]
    assert spec.name == "files"
    assert verify_capsule(SECRET, spec.url.rsplit("/", 1)[1])["cid"] == "conv-7"


def test_a_content_type_the_model_made_up_never_breaks_the_download(client, as_account):
    _call(client, _capsule(), "save_file", name="a.txt", content="x", content_type="text/plain\r\nX-Evil: 1")
    (meta,) = client.get("/files").json()["files"]
    assert meta["contentType"] == "application/octet-stream"
    assert client.get(f"/files/{meta['id']}").status_code == 200


def test_the_spec_holds_still_inside_a_window_so_the_warm_client_survives(monkeypatch):
    """AIRE rebuilds its pooled client when a turn's remote-tool URL changes."""
    monkeypatch.setenv("OG118_MCP_TOKEN", SECRET)
    monkeypatch.setenv("OG118_PUBLIC_URL", "https://api.example.org")
    monkeypatch.setenv("OG118_JOB_RESOURCE_ID", "/subscriptions/x/jobs/w")
    import background_jobs
    from runner import background_tool_spec, files_tool_spec

    reloj = {"t": 1_800_000_000.0}
    monkeypatch.setattr(background_jobs.time, "time", lambda: reloj["t"])
    first = (files_tool_spec("acct-A", "conv-1")[0].url, background_tool_spec("acct-A", "conv-1", None)[0].url)
    reloj["t"] += 600
    assert (files_tool_spec("acct-A", "conv-1")[0].url, background_tool_spec("acct-A", "conv-1", None)[0].url) == first
    assert verify_capsule(SECRET, first[0].rsplit("/", 1)[1], now=reloj["t"] + 1700) is not None
    reloj["t"] += 1800
    assert files_tool_spec("acct-A", "conv-1")[0].url != first[0]
    assert files_tool_spec("acct-A", "conv-2")[0].url != files_tool_spec("acct-A", "conv-1")[0].url

