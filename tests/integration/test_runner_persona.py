"""Runner multi-persona (Khimeras): persona_id resolution + pool keying.

A turn may carry a `persona_id` so a sibling persona (e.g. "vultur") answers
instead of Insult. Two safety-critical properties, each with a resistance case:

- Resolution: a valid id loads PERSONAS_DIR/<id>.md; None / path-traversal /
  unknown id ALL fall back to Insult's PERSONA_PATH (no directory escape, no
  silent Insult-impersonation without a log).
- Pool keying: Insult (None) keeps the bare channel_id slot (backward-compat,
  existing sessions untouched); a sibling gets channel_id:persona_id so it never
  shares Insult's SDK session in the same channel.
"""

from __future__ import annotations

from persona_runner import runner


def test_pool_key_insult_is_bare_channel():
    # Insult keeps the exact channel_id — existing sessions/behavior unchanged.
    assert runner._pool_key("chan123", None) == "chan123"


def test_pool_key_sibling_is_namespaced():
    assert runner._pool_key("chan123", "vultur") == "chan123:vultur"
    # Different personas in the same channel never collide.
    assert runner._pool_key("chan123", "vultur") != runner._pool_key("chan123", "reaper")


def test_resolve_persona_none_is_insult():
    assert runner._resolve_persona_path(None) == runner.PERSONA_PATH


def test_resolve_persona_rejects_path_traversal():
    # RESISTANCE: a crafted id must never escape PERSONAS_DIR.
    for evil in ("../../etc/passwd", "..%2f..", "a/b", "VULTUR", "with space", "x" * 40):
        assert runner._resolve_persona_path(evil) == runner.PERSONA_PATH


def test_resolve_persona_unknown_falls_back_to_insult():
    # RESISTANCE: a well-formed but nonexistent id falls back (and logs upstream).
    assert runner._resolve_persona_path("nope_zzz") == runner.PERSONA_PATH


def test_resolve_persona_loads_valid_sibling(tmp_path, monkeypatch):
    # POSITIVE: a valid id whose file exists resolves to that file.
    monkeypatch.setattr(runner, "PERSONAS_DIR", tmp_path)
    (tmp_path / "vultur.md").write_text("# Vultur\nyo soy el buitre", encoding="utf-8")
    resolved = runner._resolve_persona_path("vultur")
    assert resolved == tmp_path / "vultur.md"
    assert runner._load_persona("vultur").startswith("# Vultur")


def test_load_persona_none_uses_insult_path(tmp_path, monkeypatch):
    # POSITIVE/back-compat: None loads the default Insult persona file.
    insult_md = tmp_path / "persona.md"
    insult_md.write_text("INSULT DNA", encoding="utf-8")
    monkeypatch.setattr(runner, "PERSONA_PATH", insult_md)
    assert runner._load_persona(None) == "INSULT DNA"
