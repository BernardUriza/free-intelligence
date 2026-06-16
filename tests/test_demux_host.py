"""Unit tests for the demux host launcher (PR-3 runtime wiring + PR-3c IoC).

The host's contract: select a persona explicitly, then boot it through the
neutral ``khimeras_shared.persona.app.PersonaAppFactory`` contract WITHOUT
statically importing any persona. The no-static-import half is enforced by
``tests/arch/test_arch_import_boundaries.py``; here we test the selection logic
and the importlib-based factory launch, mocking out the actual persona boot.
"""

from __future__ import annotations

import pytest

from demux_ai import host, registry
from khimeras_shared.persona.app import PersonaApp, PersonaAppFactory


def test_registry_has_insult_and_alice():
    ids = {a.persona_id for a in registry.all_persona_apps()}
    assert {"insult", "alice"} <= ids


def test_default_persona_is_insult():
    assert registry.DEFAULT_PERSONA == "insult"


def test_entrypoints_point_at_persona_factories():
    for spec in registry.all_persona_apps():
        module, sep, attr = spec.entrypoint.partition(":")
        assert sep == ":", f"{spec.persona_id} entrypoint not 'module:callable'"
        assert module == f"personas.{spec.persona_id}.persona_app", spec.entrypoint
        assert attr == "build_app", spec.entrypoint


def test_resolve_persona_defaults_to_insult(monkeypatch):
    monkeypatch.delenv(host.PERSONA_ENV, raising=False)
    assert host.resolve_persona().persona_id == "insult"


def test_resolve_persona_explicit_wins(monkeypatch):
    monkeypatch.setenv(host.PERSONA_ENV, "insult")
    assert host.resolve_persona("alice").persona_id == "alice"


def test_resolve_persona_reads_env(monkeypatch):
    monkeypatch.setenv(host.PERSONA_ENV, "alice")
    assert host.resolve_persona().persona_id == "alice"


def test_resolve_persona_is_case_insensitive_and_trims(monkeypatch):
    monkeypatch.delenv(host.PERSONA_ENV, raising=False)
    assert host.resolve_persona("  ALICE ").persona_id == "alice"


def test_resolve_persona_unknown_raises(monkeypatch):
    monkeypatch.delenv(host.PERSONA_ENV, raising=False)
    with pytest.raises(ValueError, match="unknown persona 'ghost'"):
        host.resolve_persona("ghost")


def test_load_factory_malformed_raises():
    with pytest.raises(ValueError, match="malformed entrypoint"):
        host._load_factory("personas.insult.persona_app")


def test_load_factory_non_callable_raises(monkeypatch):
    class FakeModule:
        build_app = 42

    monkeypatch.setattr(host.importlib, "import_module", lambda name: FakeModule())
    with pytest.raises(ValueError, match="does not resolve to a callable"):
        host._load_factory("fake.module:build_app")


def _fake_module_with_factory(captured: dict):
    class FakeApp:
        def run(self):
            captured["ran"] = True

    class FakeModule:
        @staticmethod
        def build_app():
            captured["built"] = True
            return FakeApp()

    return FakeModule


def test_launch_resolves_factory_then_runs_app(monkeypatch):
    """launch() selects insult by default, calls its factory, and runs the
    returned app — without importing a real persona (importlib is mocked)."""
    monkeypatch.delenv(host.PERSONA_ENV, raising=False)
    monkeypatch.setattr(host, "configure_structlog", lambda *a, **k: None)

    captured: dict = {}

    def fake_import(name):
        captured["module"] = name
        return _fake_module_with_factory(captured)

    monkeypatch.setattr(host.importlib, "import_module", fake_import)

    host.launch()

    assert captured["module"] == "personas.insult.persona_app"
    assert captured.get("built") is True
    assert captured.get("ran") is True


def test_launch_explicit_alice(monkeypatch):
    monkeypatch.setattr(host, "configure_structlog", lambda *a, **k: None)
    captured: dict = {}

    monkeypatch.setattr(
        host.importlib,
        "import_module",
        lambda name: captured.update(module=name) or _fake_module_with_factory(captured),
    )

    host.launch("alice")

    assert captured["module"] == "personas.alice.persona_app"
    assert captured.get("ran") is True


# --- PR-3c IoC contract -------------------------------------------------------


def test_insult_factory_returns_persona_app():
    from personas.insult.persona_app import build_app

    app = build_app()
    assert isinstance(app, PersonaApp)  # runtime_checkable: has run()
    assert app.persona_id == "insult"


def test_alice_factory_returns_persona_app():
    from personas.alice.persona_app import build_app

    app = build_app()
    assert isinstance(app, PersonaApp)
    assert app.persona_id == "alice"


def test_build_app_is_a_persona_app_factory():
    from personas.insult.persona_app import build_app

    assert isinstance(build_app, PersonaAppFactory)  # runtime_checkable: callable
