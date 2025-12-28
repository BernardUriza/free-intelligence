import json
import re

import pytest
from backend.app.main import app
from backend.observability.log_spec import REQUIRED_FIELDS
from fastapi.testclient import TestClient

client = TestClient(app)


def _json_lines(captured: str):
    for line in captured.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            yield json.loads(line)
        except Exception:
            continue


def _assert_logshape(entry: dict):
    for k in REQUIRED_FIELDS:
        assert k in entry, f"missing field: {k}"
    assert re.match(r"^\d{4}-\d{2}-\d{2}T", entry["ts"])


def _pluck(lines, event):
    return [x for x in lines if x.get("event") == event]


@pytest.mark.parametrize("persona", ["clinical_advisor"])
def test_golden_chat_emits_all_events(capfd, persona):
    res = client.post(
        "/api/workflows/aurity/assistant/chat",
        json={"persona": persona, "message": "hola", "response_mode": "concise"},
    )
    assert res.status_code == 200
    out, _ = capfd.readouterr()
    logs = list(_json_lines(out))
    assert any(x.get("event") == "CHAT_REQUEST" for x in logs)
    assert any(x.get("event") == "LLM_CALL" for x in logs)
    assert any(x.get("event") == "CHAT_RESPONSE" for x in logs)
    # shape estricto de al menos el último
    _assert_logshape(logs[-1])


def test_persona_invalida_da_400_y_error(capfd):
    res = client.post(
        "/api/workflows/aurity/assistant/chat",
        json={"persona": "no_such_persona", "message": "hola"},
    )
    assert res.status_code == 400
    out, _ = capfd.readouterr()
    logs = list(_json_lines(out))
    errs = _pluck(logs, "CHAT_ERROR")
    assert errs, "esperaba CHAT_ERROR"
    # No texto literal ni previews en prod (FI_DEBUG=0)
    for e in errs:
        assert "prompt_preview" not in e
        assert "rag_preview" not in e


def test_response_mode_fallback_a_explanatory(capfd, monkeypatch):
    # Modo raro → el build debe degradar a explanatory y loggear ese mode
    res = client.post(
        "/api/workflows/aurity/assistant/chat",
        json={"persona": "general_assistant", "message": "texto", "response_mode": "weird"},
    )
    assert res.status_code in (200, 202)
    out, _ = capfd.readouterr()
    logs = list(_json_lines(out))
    reqs = _pluck(logs, "CHAT_REQUEST")
    assert reqs, "falta CHAT_REQUEST"
    # el campo response_mode ya resuelto debería ser 'explanatory'
    assert any(r.get("response_mode") == "explanatory" for r in reqs)


def test_timeout_mapea_502_y_llm_call_con_status_timeout(capfd, monkeypatch):
    # monkeypatch del cliente LLM para simular timeout
    import backend.clients.internal_llm_client as mod

    async def fake_chat(*a, **kw):
        # simula timeout upstream lanzando excepción de tu dominio
        from backend.errors import LLMTimeout

        raise LLMTimeout("sim-timeout")

    monkeypatch.setattr(mod.InternalLLMClient, "chat", fake_chat, raising=True)
    res = client.post(
        "/api/workflows/aurity/assistant/chat",
        json={"persona": "clinical_advisor", "message": "provoca timeout"},
    )
    assert res.status_code == 502
    out, _ = capfd.readouterr()
    logs = list(_json_lines(out))
    llm = _pluck(logs, "LLM_CALL")
    assert any(x.get("status") == "timeout" for x in llm), "LLM_CALL debe marcar timeout"
    err = _pluck(logs, "CHAT_ERROR")
    assert err and err[-1].get("status") == "502"
