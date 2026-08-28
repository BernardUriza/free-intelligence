"""Runner multi-persona (Khimeras): persona_id resolution.

A turn may carry a `persona_id` so a sibling persona (e.g. "vultur") answers
instead of Insult. Resolution is safety-critical: a valid id loads
PERSONAS_DIR/<id>.md; None / path-traversal / unknown id ALL fall back to
Insult's PERSONA_PATH (no directory escape, no silent Insult-impersonation
without a log). The casita naming that keeps siblings apart on the AIRE route
is pinned in tests/agent/test_aire_route.py (chat_casita tests).
"""

from __future__ import annotations

from persona_runner.core import config as runner_config
from persona_runner.engine import persona_files


def test_resolve_persona_none_is_insult():
    assert persona_files.resolve_persona_path(None) == runner_config.PERSONA_PATH


def test_resolve_persona_rejects_path_traversal():
    # RESISTANCE: a crafted id must never escape PERSONAS_DIR.
    for evil in ("../../etc/passwd", "..%2f..", "a/b", "VULTUR", "with space", "x" * 40):
        assert persona_files.resolve_persona_path(evil) == runner_config.PERSONA_PATH


def test_resolve_persona_unknown_falls_back_to_insult():
    # RESISTANCE: a well-formed but nonexistent id falls back (and logs upstream).
    assert persona_files.resolve_persona_path("nope_zzz") == runner_config.PERSONA_PATH


def test_resolve_persona_loads_valid_sibling(tmp_path, monkeypatch):
    # POSITIVE: a valid id whose file exists resolves to that file.
    monkeypatch.setattr(runner_config, "PERSONAS_DIR", tmp_path)
    (tmp_path / "vultur.md").write_text("# Vultur\nyo soy el buitre", encoding="utf-8")
    resolved = persona_files.resolve_persona_path("vultur")
    assert resolved == tmp_path / "vultur.md"
    assert persona_files.load_persona("vultur").startswith("# Vultur")


def test_load_persona_none_uses_insult_path(tmp_path, monkeypatch):
    # POSITIVE/back-compat: None loads the default Insult persona file.
    insult_md = tmp_path / "persona.md"
    insult_md.write_text("INSULT DNA", encoding="utf-8")
    monkeypatch.setattr(runner_config, "PERSONA_PATH", insult_md)
    assert persona_files.load_persona(None) == "INSULT DNA"
