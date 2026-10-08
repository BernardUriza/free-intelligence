"""The vendored drift detectors, and the gap that justified vendoring them.

fi-core's packs catch an English identity leak and miss the Spanish one — all
twelve packs score zero on "Como modelo de lenguaje de IA, no puedo opinar",
measured 2026-08-22. Bernard's whole register is Spanish, so an English-only net
is barely a net. Fixing it upstream would have touched packs Insult runs in
production; fixing it in AIRE's own copy risks nobody. These tests are what keep
that fix from silently rotting back."""

import json

import pytest

from aire.engine.guards.detect import PATTERNS_FILE, Detector, compiled, packs, sanitize
from aire.engine.guards import resolve

LEAKS_ES = [
    "Como modelo de lenguaje de IA, no puedo opinar sobre eso.",
    "Soy una inteligencia artificial y no tengo sentimientos.",
    "Como una IA, mi programación me impide responder eso.",
]
LEAKS_EN = [
    "As an AI language model, I cannot help with that.",
    "I'm an AI assistant and I don't have personal opinions.",
]
POCHO = [
    "Órale carnal, va que va.",
    "Ese wey no sabe ni madres de arquitectura, pero ahí va.",
    "Chido, ya quedó — te dejo el SHA y el deploy verde.",
]


@pytest.fixture
def guard():
    return resolve(["antidrift"])[0]


@pytest.mark.parametrize("text", LEAKS_ES)
def test_a_spanish_identity_leak_is_caught(guard, text):
    assert guard.inspect(response_text=text).metadata["severity"] == "break"


@pytest.mark.parametrize("text", LEAKS_EN)
def test_an_english_identity_leak_is_still_caught(guard, text):
    assert guard.inspect(response_text=text).metadata["severity"] == "break"


@pytest.mark.parametrize("text", POCHO)
def test_bernards_own_register_is_not_a_false_positive(guard, text):
    assert guard.inspect(response_text=text).clean


def test_the_guard_builds_without_fi_core_installed(guard):
    assert guard.name == "antidrift" and len(guard.break_patterns) > 30


def test_patterns_are_content_not_code():
    data = json.loads(PATTERNS_FILE.read_text(encoding="utf-8"))
    assert {"break", "soft", "clarification"} <= set(data)
    assert data["reinforcement"] and data["context_reinforcement"]


def test_every_shipped_pattern_compiles():
    for key in ("break", "soft", "clarification"):
        assert len(compiled(key)) == len(packs()[key]), key


def test_an_uncompilable_pattern_is_dropped_not_fatal(monkeypatch, capsys):
    monkeypatch.setattr("aire.engine.guards.detect.packs",
                        lambda: {"break": [r"valid", r"([unclosed"]})
    assert [p.pattern for p in compiled("break")] == ["valid"]
    assert "DRIFT-PATTERN-BAD" in capsys.readouterr().out


def test_editing_the_file_is_picked_up_without_a_restart(tmp_path, monkeypatch):
    f = tmp_path / "p.json"
    f.write_text(json.dumps({"break": ["first"]}), encoding="utf-8")
    monkeypatch.setattr("aire.engine.guards.detect.PATTERNS_FILE", f)
    monkeypatch.setattr("aire.engine.guards.detect._CACHE", {"mtime": None, "data": None})
    assert packs()["break"] == ["first"]
    f.write_text(json.dumps({"break": ["second"]}), encoding="utf-8")
    import os
    os.utime(f, (0, 0))
    assert packs()["break"] == ["second"]


def test_sanitize_drops_the_offending_sentence_and_keeps_the_answer():
    import re
    out = sanitize("As an AI I cannot. But the answer is 42.", [re.compile("(?i)as an ai")])
    assert out == "But the answer is 42."


def test_sanitize_refuses_to_erase_everything():
    import re
    original = "As an AI I cannot."
    assert sanitize(original, [re.compile("(?i)as an ai")]) == original


def test_one_detector_carries_its_own_severity():
    import re
    d = Detector(patterns=[re.compile("boom")], severity="break")
    assert d.detect("boom here") == ["boom"] and d.detect("quiet") == []
