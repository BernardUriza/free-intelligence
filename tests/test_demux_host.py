"""Unit tests for the demux host launcher (PR-3 runtime wiring).

The host's contract: select a persona explicitly, then boot its app entrypoint
WITHOUT statically importing any persona. The no-static-import half is enforced
by ``tests/arch/test_arch_import_boundaries.py``; here we test the selection
logic and the importlib-based launch, mocking out the actual persona boot.
"""

from __future__ import annotations

import pytest

from demux_ai import host, registry


def test_registry_has_insult_and_alice():
    ids = {a.persona_id for a in registry.all_persona_apps()}
    assert {"insult", "alice"} <= ids


def test_default_persona_is_insult():
    assert registry.DEFAULT_PERSONA == "insult"


def test_entrypoints_are_module_callable_strings():
    for app in registry.all_persona_apps():
        module, sep, attr = app.entrypoint.partition(":")
        assert sep == ":", f"{app.persona_id} entrypoint not 'module:callable'"
        assert module.startswith(f"personas.{app.persona_id}"), app.entrypoint
        assert attr, app.entrypoint


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


def test_load_entrypoint_malformed_raises():
    with pytest.raises(ValueError, match="malformed entrypoint"):
        host._load_entrypoint("personas.insult.__main__")


def test_load_entrypoint_non_callable_raises(monkeypatch):
    class FakeModule:
        not_callable = 42

    monkeypatch.setattr(host.importlib, "import_module", lambda name: FakeModule())
    with pytest.raises(ValueError, match="does not resolve to a callable"):
        host._load_entrypoint("fake.module:not_callable")


def test_launch_resolves_then_calls_entrypoint(monkeypatch):
    """launch() must select insult by default and call the resolved callable —
    without ever importing a real persona (importlib is mocked)."""
    monkeypatch.delenv(host.PERSONA_ENV, raising=False)
    monkeypatch.setattr(host, "configure_structlog", lambda *a, **k: None)

    booted = {"called": False}

    class FakeMain:
        @staticmethod
        def run():
            booted["called"] = True

    captured = {}

    def fake_import(name):
        captured["module"] = name
        return FakeMain

    monkeypatch.setattr(host.importlib, "import_module", fake_import)

    host.launch()

    assert booted["called"] is True
    assert captured["module"] == "personas.insult.__main__"


def test_launch_explicit_alice(monkeypatch):
    monkeypatch.setattr(host, "configure_structlog", lambda *a, **k: None)
    captured = {}

    class FakeMain:
        @staticmethod
        def run():
            captured["ran"] = True

    monkeypatch.setattr(host.importlib, "import_module", lambda name: captured.update(module=name) or FakeMain)

    host.launch("alice")

    assert captured["module"] == "personas.alice.__main__"
    assert captured.get("ran") is True
