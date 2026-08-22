"""FENIX_BACKEND=aire — el turno de Fénix viaja por la puerta del engine de AIRE.

La migración de og118 (fi PRs #409/#411/#413, aire-server backlog #35) es la
plantilla y Fénix la hereda entera, porque corre el MISMO runtime: sin
FENIX_BACKEND la ruta es byte-idéntica a la de hoy (BackendAcotado sobre el CLI
con ANTHROPIC_API_KEY); con FENIX_BACKEND=aire, `configurar_motor()` traduce el
contrato de esta app a las variables del runtime (OG118_BACKEND /
OG118_AIRE_PROJECT) ANTES de importar `app`, y entonces:

- la casita base es `fenix` (la persona del mostrador, compuesta con las
  constraints y la identidad viva, vive UNA vez ahí);
- cada chat nace DELGADO en `fenix-{conversationId}` con el stub `@base fenix`
  que AIRE dereferencia en cada spawn;
- el tutor del cibercafé —segunda persona en el mismo proceso— tiene SU casita
  base `fenix-tutor`, para que las dos voces no se peleen un solo /init.

Unit/mock only — nada toca la puerta real.
"""

from __future__ import annotations

import os
from typing import Any

import pytest
from fi_runner import AIREBackend

from arranque import configurar_motor
from runner import BackendAcotado, aire_project_for_chat, build_runner

# --- configurar_motor: el contrato FENIX_* traducido al runtime ---------------


def test_sin_fenix_backend_no_toca_el_entorno(monkeypatch) -> None:
    monkeypatch.delenv("FENIX_BACKEND", raising=False)
    monkeypatch.delenv("OG118_BACKEND", raising=False)
    monkeypatch.delenv("OG118_AIRE_PROJECT", raising=False)
    configurar_motor()
    assert "OG118_BACKEND" not in os.environ
    assert "OG118_AIRE_PROJECT" not in os.environ


def test_fenix_backend_aire_traduce_a_las_variables_del_runtime(monkeypatch) -> None:
    monkeypatch.setenv("FENIX_BACKEND", "aire")
    monkeypatch.delenv("FENIX_AIRE_PROJECT", raising=False)
    monkeypatch.delenv("OG118_BACKEND", raising=False)
    monkeypatch.delenv("OG118_AIRE_PROJECT", raising=False)
    configurar_motor()
    assert os.environ["OG118_BACKEND"] == "aire"
    assert os.environ["OG118_AIRE_PROJECT"] == "fenix"


def test_fenix_aire_project_respeta_el_entorno(monkeypatch) -> None:
    monkeypatch.setenv("FENIX_BACKEND", "aire")
    monkeypatch.setenv("FENIX_AIRE_PROJECT", "fenix-staging")
    configurar_motor()
    assert os.environ["OG118_AIRE_PROJECT"] == "fenix-staging"


# --- la ruta aire completa: casita base fenix, chats fenix-{id} ---------------


@pytest.fixture
def motor_aire(monkeypatch):
    monkeypatch.setenv("FENIX_BACKEND", "aire")
    monkeypatch.delenv("FENIX_AIRE_PROJECT", raising=False)
    monkeypatch.delenv("OG118_AIRE_PROJECT", raising=False)
    monkeypatch.delenv("OG118_BACKEND", raising=False)
    configurar_motor()


def test_la_ruta_aire_lleva_la_identidad_fenix(motor_aire) -> None:
    runner = build_runner()
    assert isinstance(runner.backend, AIREBackend)
    assert runner.backend.project == "fenix"
    assert runner.backend.default_mode == "complete"
    assert runner.backend.registry_tools == ("persona",)
    # AIRE es dueño de las tools server-side: el MCP local de expedientes
    # (guardar_cotizacion) y el rag_store NO cruzan la puerta.
    assert runner.capabilities == []


def test_los_chats_se_nombran_con_el_prefijo_fenix(motor_aire) -> None:
    assert aire_project_for_chat("abc-123") == "fenix-abc-123"


def test_sin_motor_la_ruta_es_byte_identica(monkeypatch) -> None:
    for var in ("FENIX_BACKEND", "OG118_BACKEND", "OG118_AIRE_PROJECT"):
        monkeypatch.delenv(var, raising=False)
    configurar_motor()
    runner = build_runner(capabilities=["task_tracker"], extra_mcp_servers=[])
    assert isinstance(runner.backend, BackendAcotado)
    assert runner.capabilities == ["task_tracker"]
    assert aire_project_for_chat("abc") == "og118-abc"


# --- el tutor: segunda persona, segunda casita base ---------------------------


def test_el_tutor_tiene_su_propia_casita_base(motor_aire) -> None:
    runner = build_runner(
        persona_text="Eres el tutor del cibercafé.",
        capabilities=["task_tracker"],
        extra_mcp_servers=[],
        aire_project="fenix-tutor",
    )
    assert isinstance(runner.backend, AIREBackend)
    assert runner.backend.project == "fenix-tutor"
    # También el tutor pide la tool persona y carga el párrafo de identidad viva.
    assert runner.backend.registry_tools == ("persona",)
    assert "mcp__persona__read" in runner.persona
    # En la ruta aire las capabilities locales se fuerzan a vacío aunque el
    # caller pida task_tracker: ese MCP corre local y no existe en el droplet.
    assert runner.capabilities == []


class _PostRecorder:
    """Suplanta el httpx perezoso del backend: registra los /init, contesta 200."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def post(self, url: str, *, headers: Any = None, json: Any = None) -> Any:
        self.calls.append((url, json))

        class _Res:
            status_code = 200
            text = "ok"

        return _Res()


@pytest.mark.asyncio
async def test_nacimiento_delgado_del_chat_del_tutor(motor_aire) -> None:
    """La persona del tutor se instala UNA vez en `fenix-tutor`; el chat nace
    con el stub `@base fenix-tutor` — su voz correcta, aunque el nombre del chat
    comparta el prefijo `fenix-` con los del mostrador."""
    runner = build_runner(
        persona_text="Eres el tutor del cibercafé.",
        capabilities=["task_tracker"],
        extra_mcp_servers=[],
        aire_project="fenix-tutor",
    )
    backend = runner.backend
    rec = _PostRecorder()
    backend.gate_url = "https://gate.test"
    backend.auth_token = "tok"
    backend._client = rec
    chat = aire_project_for_chat("chat-1")
    await backend._ensure_prompt(chat, runner.persona)
    await backend._ensure_prompt(chat, runner.persona)
    assert [u for u, _ in rec.calls] == [
        "https://gate.test/projects/fenix-tutor/init",
        "https://gate.test/projects/fenix-chat-1/init",
    ]
    assert rec.calls[0][1]["claude_md"] == runner.persona.strip()
    assert rec.calls[1][1] == {"claude_md": "@base fenix-tutor"}


@pytest.mark.asyncio
async def test_nacimiento_delgado_del_chat_del_mostrador(motor_aire) -> None:
    runner = build_runner(persona_text="Eres Fénix, el mostrador.")
    backend = runner.backend
    rec = _PostRecorder()
    backend.gate_url = "https://gate.test"
    backend.auth_token = "tok"
    backend._client = rec
    await backend._ensure_prompt(aire_project_for_chat("chat-2"), runner.persona)
    assert rec.calls == [
        ("https://gate.test/projects/fenix/init", {"claude_md": runner.persona.strip()}),
        ("https://gate.test/projects/fenix-chat-2/init", {"claude_md": "@base fenix"}),
    ]
