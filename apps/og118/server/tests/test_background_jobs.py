"""OG118-BACKGROUND-1 — que "te aviso cuando termine" sea verdad.

Las piezas se prueban en la costura donde cada una podría mentir: el reclamo del
job (dos ejecuciones no reclaman el mismo), la cápsula (firma y vencimiento), el
merge anti-clobber (el PUT del cliente no borra lo que el worker dejó), la puerta
MCP (404 sin bearer, error con cápsula vencida, job encolado y ejecución
arrancada cuando todo cuadra), el gating del prompt (la promesa sólo existe con
la tool) y el worker (entrega al record con la forma que el cliente persiste).
"""

from __future__ import annotations

import asyncio
import dataclasses
import json
import time

import pytest
from fastapi.testclient import TestClient

import background_jobs
import mcp_background
from background_jobs import JobStore, sign_capsule, verify_capsule
from conversations import ConversationStore

SECRET = "s3cret-bearer"


@pytest.fixture
def jobs(tmp_path, monkeypatch):
    store = JobStore(tmp_path / "jobs")
    monkeypatch.setattr(mcp_background, "_job_store", store)
    return store


@pytest.fixture
def puerta(monkeypatch):
    monkeypatch.setenv("OG118_MCP_TOKEN", SECRET)
    monkeypatch.setenv("OG118_JOB_RESOURCE_ID", "/subscriptions/x/resourceGroups/rg/providers/Microsoft.App/jobs/og118-worker")
    arranques: list[str] = []
    monkeypatch.setattr(mcp_background, "_starter", lambda rid: arranques.append(rid) or "exec-1")
    import app as app_module

    return TestClient(app_module.create_app()), arranques


def _rpc(client, capsule, method, params=None, token=SECRET):
    return client.post(
        f"/mcp/background/{capsule}",
        json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}},
        headers={"Authorization": f"Bearer {token}"} if token else {},
    )


# --- JobStore ---------------------------------------------------------------

def test_el_reclamo_es_por_orden_y_sin_repetir(jobs):
    a = jobs.create(owner="auth0|ana", conversation_id="c1", goal="uno", corpus_id=None)
    time.sleep(0.01)
    b = jobs.create(owner="auth0|ana", conversation_id="c1", goal="dos", corpus_id="p1")
    assert jobs.claim_next()["id"] == a["id"]
    assert jobs.claim_next()["id"] == b["id"]
    assert jobs.claim_next() is None
    assert jobs.get(a["id"])["status"] == "running"


def test_finish_y_fail_mueven_el_job_a_su_estado_terminal(jobs):
    job = jobs.create(owner="o", conversation_id="c", goal="g", corpus_id=None)
    claimed = jobs.claim_next()
    jobs.finish(claimed, "resultado")
    assert jobs.get(job["id"])["status"] == "done"
    assert jobs.get(job["id"])["result"] == "resultado"
    otro = jobs.create(owner="o", conversation_id="c", goal="g2", corpus_id=None)
    jobs.fail(jobs.claim_next(), "boom")
    assert jobs.get(otro["id"])["status"] == "failed"
    assert jobs.pending_for("o", "c") == []


def test_un_goal_vacio_no_se_encola(jobs):
    with pytest.raises(ValueError):
        jobs.create(owner="o", conversation_id="c", goal="   ", corpus_id=None)


# --- Cápsula ----------------------------------------------------------------

def test_la_capsula_identifica_y_vence():
    cap = sign_capsule(SECRET, sub="auth0|ana", conversation_id="c1", corpus_id="p1", now=1000.0)
    assert verify_capsule(SECRET, cap, now=1500.0) == {"sub": "auth0|ana", "cid": "c1", "corpus": "p1", "exp": 1000 + 1800}
    assert verify_capsule(SECRET, cap, now=1000.0 + 1801) is None
    assert verify_capsule("otro-secreto", cap, now=1500.0) is None
    body, mac = cap.rsplit(".", 1)
    assert verify_capsule(SECRET, f"{body}x.{mac}", now=1500.0) is None
    assert verify_capsule("", cap, now=1500.0) is None


# --- ConversationStore: append + anti-clobber -------------------------------

def _record(cid="c1", msgs=None, updated="2026-09-12T10:00:00.000Z"):
    return {
        "id": cid, "title": "t", "createdAt": "2026-09-12T09:00:00.000Z", "updatedAt": updated,
        "messages": msgs or [{"role": "user", "content": "hola", "timestamp": "2026-09-12T09:00:00.000Z"}],
        "preview": "hola", "schemaVersion": 1,
    }


def test_append_message_marca_origen_y_mueve_updatedAt_y_preview(tmp_path):
    store = ConversationStore(tmp_path)
    store.put("o", _record())
    out = store.append_message("o", "c1", {"role": "assistant", "content": "Listo: el resultado", "timestamp": "2026-09-12T11:00:00.000Z"})
    assert out["messages"][-1]["origin"] == "background"
    assert out["updatedAt"] == "2026-09-12T11:00:00.000Z"
    assert out["preview"] == "Listo: el resultado"
    assert store.append_message("o", "nope", {"role": "assistant", "content": "x", "timestamp": "z"}) is None


def test_el_PUT_del_cliente_no_borra_lo_que_el_worker_dejo(tmp_path):
    store = ConversationStore(tmp_path)
    store.put("o", _record())
    store.append_message("o", "c1", {"role": "assistant", "content": "del worker", "timestamp": "2026-09-12T11:00:00.000Z"})
    # El cliente manda su copia vieja + un turno nuevo, sin haber recargado.
    cliente = _record(msgs=[
        {"role": "user", "content": "hola", "timestamp": "2026-09-12T09:00:00.000Z"},
        {"role": "user", "content": "y luego", "timestamp": "2026-09-12T12:00:00.000Z"},
        {"role": "assistant", "content": "pues", "timestamp": "2026-09-12T12:00:01.000Z"},
    ], updated="2026-09-12T12:00:01.000Z")
    merged = store.put_content("o", cliente)
    contenidos = [m["content"] for m in merged["messages"]]
    assert contenidos == ["hola", "del worker", "y luego", "pues"]
    # Ya recargado, el cliente lo trae (sin `origin`, que su sanitizer tira): no se duplica.
    recargado = _record(msgs=[{k: v for k, v in m.items() if k != "origin"} for m in merged["messages"]])
    otra_vez = store.put_content("o", recargado)
    assert [m["content"] for m in otra_vez["messages"]] == contenidos


# --- La puerta MCP ------------------------------------------------------------

def test_sin_bearer_la_puerta_no_existe(puerta):
    client, _ = puerta
    assert _rpc(client, "cualquier", "tools/list", token=None).status_code == 404
    assert _rpc(client, "cualquier", "tools/list", token="malo").status_code == 404


def test_tools_list_expone_solo_start_background_task(puerta):
    client, _ = puerta
    r = _rpc(client, "cualquier", "tools/list")
    assert r.status_code == 200
    tools = r.json()["result"]["tools"]
    assert [t["name"] for t in tools] == ["start_background_task"]
    assert tools[0]["inputSchema"]["required"] == ["goal"]


def test_una_capsula_vencida_contesta_error_sin_encolar(puerta, jobs):
    client, arranques = puerta
    cap = sign_capsule(SECRET, sub="auth0|ana", conversation_id="c1", corpus_id=None, now=time.time() - 7200)
    r = _rpc(client, cap, "tools/call", {"name": "start_background_task", "arguments": {"goal": "investiga"}})
    assert r.json()["result"]["isError"] is True
    assert arranques == [] and jobs.claim_next() is None


def test_con_capsula_viva_encola_y_arranca_la_ejecucion(puerta, jobs):
    client, arranques = puerta
    cap = sign_capsule(SECRET, sub="auth0|ana", conversation_id="c1", corpus_id="p9")
    r = _rpc(client, cap, "tools/call", {"name": "start_background_task", "arguments": {"goal": "investiga X"}})
    res = r.json()["result"]
    assert res["isError"] is False and "Queued" in res["content"][0]["text"]
    assert arranques == ["/subscriptions/x/resourceGroups/rg/providers/Microsoft.App/jobs/og118-worker"]
    job = jobs.claim_next()
    assert (job["owner"], job["conversationId"], job["corpusId"], job["goal"]) == ("auth0|ana", "c1", "p9", "investiga X")


def test_si_el_job_no_arranca_la_tool_lo_dice_y_el_job_queda_failed(puerta, jobs, monkeypatch):
    client, _ = puerta

    def explota(rid):
        raise RuntimeError("403 from ARM")

    monkeypatch.setattr(mcp_background, "_starter", explota)
    cap = sign_capsule(SECRET, sub="auth0|ana", conversation_id="c1", corpus_id=None)
    r = _rpc(client, cap, "tools/call", {"name": "start_background_task", "arguments": {"goal": "algo"}})
    assert r.json()["result"]["isError"] is True
    assert jobs.claim_next() is None
    failed = [p for p in (jobs._root / "failed").glob("*.json")]
    assert len(failed) == 1 and "403" in json.loads(failed[0].read_text())["error"]


# --- El prompt y el spec por turno -------------------------------------------

def test_sin_infra_el_prompt_prohibe_prometer_y_no_hay_spec(monkeypatch):
    for v in ("OG118_MCP_TOKEN", "OG118_PUBLIC_URL", "OG118_JOB_RESOURCE_ID"):
        monkeypatch.delenv(v, raising=False)
    from runner import background_disponible, background_tool_spec, build_runner

    assert background_disponible() is False
    assert "NO BACKGROUND, NO LATER" in build_runner().persona
    assert "start_background_task" not in build_runner().persona
    assert background_tool_spec("auth0|ana", "c1", None) == []


def test_con_infra_el_prompt_ensena_la_tool_y_el_spec_lleva_la_capsula(monkeypatch):
    monkeypatch.setenv("OG118_MCP_TOKEN", SECRET)
    monkeypatch.setenv("OG118_PUBLIC_URL", "https://api.example.org/")
    monkeypatch.setenv("OG118_JOB_RESOURCE_ID", "/subscriptions/x/jobs/w")
    from runner import background_tool_spec, build_runner

    persona = build_runner().persona
    assert "mcp__background__start_background_task" in persona and "NO BACKGROUND, NO LATER" not in persona
    assert "NO BACKGROUND, NO LATER" in build_runner(background=False).persona
    (spec,) = background_tool_spec("auth0|ana", "c1", "p1")
    assert spec.is_http and spec.name == "background"
    capsule = spec.url.removeprefix("https://api.example.org/mcp/background/")
    assert verify_capsule(SECRET, capsule)["cid"] == "c1"
    assert spec.headers == {"Authorization": f"Bearer {SECRET}"}
    assert background_tool_spec("auth0|ana", None, None) == []


def test_el_turno_local_monta_el_spec_remoto(monkeypatch, tmp_path):
    """La ruta /chat/stream le entrega al runner del turno el MCP remoto con la
    cápsula de ESTE principal y ESTA conversación."""
    monkeypatch.setenv("OG118_MCP_TOKEN", SECRET)
    monkeypatch.setenv("OG118_PUBLIC_URL", "https://api.example.org")
    monkeypatch.setenv("OG118_JOB_RESOURCE_ID", "/subscriptions/x/jobs/w")
    from fi_runner import Runner
    import app as app_module

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
        with TestClient(app_module.app) as client:
            r = client.post("/chat/stream", json={"message": "hola", "session_id": "conv-7"})
    finally:
        app_module.app.dependency_overrides.pop(app_module.get_runner_selector, None)
    assert r.status_code == 200
    (spec,) = visto["extra"]
    assert verify_capsule(SECRET, spec.url.rsplit("/", 1)[1])["cid"] == "conv-7"


# --- El worker -----------------------------------------------------------------

def test_el_worker_entrega_al_record_y_cierra_el_job(tmp_path, monkeypatch, jobs, project_registry):
    import app as app_module
    import background_worker

    conversations = ConversationStore(tmp_path / "conv")
    monkeypatch.setattr(app_module, "_conversation_store", conversations)
    monkeypatch.setattr(app_module, "_project_registry", project_registry)
    conversations.put("auth0|ana", _record(cid="c1"))
    jobs.create(owner="auth0|ana", conversation_id="c1", goal="resume el hilo", corpus_id=None)
    jobs.create(owner="auth0|ana", conversation_id="borrada", goal="x", corpus_id=None)

    llamadas: list[dict] = []

    class _Runner:
        async def run(self, prompt, **kw):
            llamadas.append({"prompt": prompt, **kw})
            return dataclasses.make_dataclass("R", ["text", "answer"])("razonando… Aquí va", "Aquí va el resumen")

    hechos = asyncio.run(background_worker.drenar(runner=_Runner()))
    assert hechos == 1
    assert "resume el hilo" in llamadas[0]["prompt"]
    assert llamadas[0]["history"] == [{"role": "user", "content": "hola"}]
    assert llamadas[0]["session_id"] == "c1"
    record = conversations.get("auth0|ana", "c1")
    assert record["messages"][-1]["content"] == "Aquí va el resumen"
    assert record["messages"][-1]["origin"] == "background"
    estados = sorted(p.parent.name for p in (jobs._root).glob("*/*.json"))
    assert estados == ["done", "failed"]
