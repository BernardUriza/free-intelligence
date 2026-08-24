"""OG118_BACKEND selecciona el motor del turno (aire-server backlog #35).

Sin la variable (o con "claude-code") la ruta es byte-idéntica a la de siempre:
BackendAcotado sobre el CLI con OAuth ambiente, capabilities MCP locales
completas. Con "aire" el Runner habla HTTP con AIRE via AIREBackend: la
identidad viaja como proyecto ("og118" → su propia casita/memoria en el
Postgres de AIRE), y las capabilities locales se fuerzan a vacío porque la
puerta 422ea cualquier tool fuera de su registry — un task_tracker/rag_store
local no puede correr en el droplet.
"""

from __future__ import annotations

from fi_runner import AIREBackend

from runner import BackendAcotado, build_runner


def test_default_sigue_siendo_claude_code(monkeypatch) -> None:
    monkeypatch.delenv("OG118_BACKEND", raising=False)
    runner = build_runner()
    assert isinstance(runner.backend, BackendAcotado)
    assert "task_tracker" in runner.capabilities
    assert "rag_store" in runner.capabilities


def test_aire_selecciona_el_puente_con_identidad_og118(monkeypatch) -> None:
    monkeypatch.setenv("OG118_BACKEND", "aire")
    monkeypatch.delenv("OG118_AIRE_PROJECT", raising=False)
    monkeypatch.setenv("OG118_MODEL", "claude-sonnet-4-5")
    runner = build_runner()
    assert isinstance(runner.backend, AIREBackend)
    assert runner.backend.project == "og118"
    assert runner.backend.default_model == "claude-sonnet-4-5"
    assert runner.backend.default_mode == "complete"
    # AIRE es dueño de las tools server-side: nada de MCP local cruza. La única
    # tool que el turno PIDE es `persona`, del registry de AIRE — el CLAUDE.md
    # vivo de la casita del chat (OG118-LIVING-CLAUDE).
    assert runner.capabilities == []
    assert "persona" in runner.backend.registry_tools


def test_aire_respeta_el_proyecto_del_entorno(monkeypatch) -> None:
    monkeypatch.setenv("OG118_BACKEND", "aire")
    monkeypatch.setenv("OG118_AIRE_PROJECT", "og118-staging")
    runner = build_runner()
    assert runner.backend.project == "og118-staging"


def test_aire_project_del_caller_gana_sobre_el_entorno(monkeypatch) -> None:
    """La costura para un consumer con DOS personas en el mismo proceso (fenix:
    mostrador y tutor): cada runner puede fijar su propia casita base, para que
    las dos voces no se peleen un solo /init."""
    monkeypatch.setenv("OG118_BACKEND", "aire")
    monkeypatch.setenv("OG118_AIRE_PROJECT", "fenix")
    runner = build_runner(aire_project="fenix-tutor")
    assert runner.backend.project == "fenix-tutor"


# --- a binding may not promise a tool the turn does not carry -----------------
# Measured 2026-08-24: on the AIRE route a turn with an active project shipped
# ZERO mcp_servers and a system prompt ordering the model to "call
# search_documents IMMEDIATELY ... phrasings like '¿quieres que busque?' are
# FORBIDDEN". The tool does not exist there. That is not a lost feature — it is
# a persona instructed to lie about what it can do, and the user watches the
# model invent or apologise. The corpus binding now leaves with its tools.


def _addendum(runner, corpus_id: str = "proj-42") -> str:
    return runner.context_prompt({"corpus_id": corpus_id}) or ""


def test_los_dos_extremos_del_camino_aterrizan_en_aire(monkeypatch) -> None:
    """La condición no era "la tool existe" — era que la subida escriba donde la
    búsqueda lee. Con la puerta del corpus (aire-server #47) los dos extremos son
    AIRE, así que la tool y el binding vuelven JUNTOS con la costura de escritura.
    Este test los ata: si alguien devuelve el binding sin enrutar la subida, o al
    revés, falla aquí y no en la cara de un usuario."""
    monkeypatch.setenv("OG118_BACKEND", "aire")
    monkeypatch.setenv("AIRE_GATE_URL", "https://gate.example")
    monkeypatch.setenv("AIRE_AUTH_TOKEN", "tok")
    import app as og118_app
    from fi_runner.aire_corpus import AireCorpusClient

    og118_app._rag_store = None
    try:
        assert isinstance(og118_app.get_rag_store(), AireCorpusClient), \
            "la subida tiene que escribir en AIRE"
    finally:
        og118_app._rag_store = None
    runner = build_runner()
    assert "rag_store" in runner.backend.registry_tools
    assert "search_documents" in _addendum(runner) and "proj-42" in _addendum(runner)


def test_pero_las_instrucciones_del_dueno_siguen(monkeypatch) -> None:
    """Owner instructions depend on no tool, so dropping the corpus binding must
    not take them with it — that would be a second bug fixing the first."""
    monkeypatch.setenv("OG118_BACKEND", "aire")
    assert build_runner().context_prompt is not None


def test_la_ruta_local_conserva_el_binding_del_corpus(monkeypatch) -> None:
    monkeypatch.delenv("OG118_BACKEND", raising=False)
    runner = build_runner()
    addendum = _addendum(runner)
    assert "search_documents" in addendum and "proj-42" in addendum


def test_la_ruta_aire_pide_sus_tools_al_registry_de_aire(monkeypatch) -> None:
    """El plan en vivo dejó de ser una capability local que esta ruta perdía:
    AIRE lo sirve desde su registry (aire-server #45) con los mismos nombres de
    tool, así que `_derive_plan_events` lo traduce sin saber en qué puerta corrió."""
    monkeypatch.setenv("OG118_BACKEND", "aire")
    backend = build_runner().backend
    assert set(backend.registry_tools) == {"persona", "task_tracker", "rag_store"}
