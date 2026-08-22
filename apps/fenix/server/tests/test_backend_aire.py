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
  base `fenix-tutor`, para que las dos voces no se peleen un solo /init;
- y el tutor viaja en `mode=agent`, la ÚNICA muesca del dial de la puerta que
  concede WebSearch/WebFetch — sin ella «busca en internet» deja de poder, que
  es media persona del tutor. El mostrador se queda en `complete`.

Unit/mock only — nada toca la puerta real.
"""

from __future__ import annotations

import os
from typing import Any

import pytest
from fi_runner import AIREBackend

from arranque import configurar_motor
from runner import BUILTINS_DISPONIBLES, BackendAcotado, aire_project_for_chat, build_runner

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


def test_sin_motor_el_tutor_busca_por_los_builtins_de_siempre(monkeypatch) -> None:
    """La ruta claude-code no se enteró de que existe un dial de modos.

    Aquí la búsqueda del tutor no viene de la puerta sino de `BackendAcotado`,
    que fija `tools` a `BUILTINS_DISPONIBLES` — y ahí siguen WebSearch/WebFetch,
    intactos. Pedir `aire_mode` no puede cambiar esta ruta: si algún día la
    tocara, este test es el que se pone rojo."""
    for var in ("FENIX_BACKEND", "OG118_BACKEND", "OG118_AIRE_PROJECT"):
        monkeypatch.delenv(var, raising=False)
    configurar_motor()
    runner = build_runner(
        persona_text="Eres el tutor del cibercafé.",
        capabilities=["task_tracker"],
        extra_mcp_servers=[],
        aire_project="fenix-tutor",
        aire_mode="agent",
    )
    assert isinstance(runner.backend, BackendAcotado)
    assert not hasattr(runner.backend, "default_mode")
    assert set(BUILTINS_DISPONIBLES) == {"WebSearch", "WebFetch"}


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


# --- el dial de modos: quién puede buscar en internet -------------------------
#
# El dial de la puerta de AIRE (aire-server server/aire/engine/options.py, MODES)
# tiene dos muescas y son paquetes cerrados:
#
#   complete → allowed_tools []  · prohibidos Bash/Read/Write/Edit/Glob/Grep/
#                                  WebSearch/WebFetch
#   agent    → allowed_tools Read, Write, Glob, Grep, WebSearch, WebFetch
#              · prohibido Bash · permission_mode acceptEdits
#
# Estas constantes son la copia LOCAL del contrato: si aire-server mueve el
# dial, lo que se rompe es esta lista y el diff cuenta la historia. Que el
# recuperar la búsqueda arrastre los tools de archivo es el hueco nombrado en
# aire-server backlog #37 — la jaula (#24) los confina a la casita del chat.
TOOLS_MODO_AGENT = ("Read", "Write", "Glob", "Grep", "WebSearch", "WebFetch")


@pytest.fixture
def tutor_real(monkeypatch):
    """El tutor tal como lo construye `fenix_app`, no uno armado a mano.

    Lo que se prueba es el CABLEADO de producción: que `aire_mode="agent"` esté
    en la llamada real, no que `build_runner` sepa aceptarlo. Importar
    `fenix_app` corre `exigir_config()`, así que las invariantes de arranque se
    declaran igual que en el conftest de la app.

    El import va con el motor de SIEMPRE a propósito: `app` construye su
    `_runner` de módulo AL IMPORTARSE, una sola vez por proceso, así que
    dejarlo nacer en la ruta aire le quitaría el rag_store al mostrador para
    toda la suite (un test de otro archivo se puso rojo por eso). El motor se
    enciende DESPUÉS: `_tutor()` es perezoso y `build_runner` lee
    OG118_BACKEND en la llamada, no en el import."""
    monkeypatch.setenv("FENIX_ADMIN_TOKEN", "token-de-prueba")
    monkeypatch.setenv("FENIX_USO_PERSONAL", "1")
    monkeypatch.setenv("FENIX_TUTOR_ABIERTO", "1")
    monkeypatch.delenv("OG118_ACCESS_TOKEN", raising=False)
    for var in ("FENIX_BACKEND", "OG118_BACKEND", "OG118_AIRE_PROJECT"):
        monkeypatch.delenv(var, raising=False)

    import fenix_app

    monkeypatch.setenv("FENIX_BACKEND", "aire")
    configurar_motor()
    monkeypatch.setattr(fenix_app, "_runner_tutor", None)
    return fenix_app._tutor()


def test_el_tutor_vuelve_a_poder_buscar_en_internet(tutor_real) -> None:
    """«Busca en internet» sólo puede en mode=agent — y ésa es media persona
    del tutor (`tutor.md` §CUANDO BUSCAS EN INTERNET). En complete la puerta
    prohíbe WebSearch/WebFetch y el tutor ofrecería algo que no puede hacer."""
    assert isinstance(tutor_real.backend, AIREBackend)
    assert tutor_real.backend.default_mode == "agent"
    assert {"WebSearch", "WebFetch"} <= set(TOOLS_MODO_AGENT)
    # La casita base del tutor no cambia por subir el modo.
    assert tutor_real.backend.project == "fenix-tutor"
    # Y sigue pidiendo su tool del registry: el modo se suma a `tools`, no lo
    # sustituye (aire-server _mount_tools une los dos en allowed_tools).
    assert tutor_real.backend.registry_tools == ("persona",)


def test_el_modo_agent_tambien_concede_los_tools_de_archivo(tutor_real) -> None:
    """El costo, escrito para que nadie lo descubra en producción: el dial es
    grueso, así que con la búsqueda entran Read/Write/Glob/Grep. La jaula de
    AIRE (#24) los confina a la casita de ESE chat y Bash no está en ninguna
    muesca — pero se conceden, y eso se dice, no se entierra."""
    assert tutor_real.backend.default_mode == "agent"
    assert set(TOOLS_MODO_AGENT) - {"WebSearch", "WebFetch"} == {
        "Read",
        "Write",
        "Glob",
        "Grep",
    }
    assert "Bash" not in TOOLS_MODO_AGENT


def test_el_mostrador_no_sube_de_modo(motor_aire) -> None:
    """Sólo el tutor paga el paquete. El mostrador cotiza de la lista maestra y
    tiene internet prohibido por persona: subirlo a `agent` le regalaría tools
    que nadie pidió, y hoy ni siquiera está lanzado."""
    runner = build_runner()
    assert isinstance(runner.backend, AIREBackend)
    assert runner.backend.project == "fenix"
    assert runner.backend.default_mode == "complete"


def test_el_modo_por_defecto_de_la_ruta_aire_sigue_siendo_complete(motor_aire) -> None:
    """La costura es opt-in: un caller que no nombra el modo queda como estaba,
    así que og118 —que corre este mismo `build_runner`— no se movió."""
    runner = build_runner(
        persona_text="Cualquier voz.",
        aire_project="fenix-lo-que-sea",
    )
    assert runner.backend.default_mode == "complete"
