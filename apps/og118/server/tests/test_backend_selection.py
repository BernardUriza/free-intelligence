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
    assert runner.backend.registry_tools == ("persona",)


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
