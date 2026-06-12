"""PR-E PresetEnginePort — positive (arbitration) + resistance (boundary).

Second capability seam (`.claude/plans/capability_seams_retrieval_preset.md`):
preset classification + guidance rendering as ONE logical operation behind
``PresetEnginePort``. The dual strategy (LLM judge + rule-based regex), the
timeout/cancel, the fallback and the divergence telemetry live INSIDE the
adapter (``insult.composition``); stages only schedules ``resolve`` early via
a plain ``asyncio.Task`` and consumes the result.

Each behavior gets a positive case AND a resistance case per
.claude/rules/robustness.md.
"""

from __future__ import annotations

import ast
import asyncio
import types
from pathlib import Path

from personas.insult.composition import build_preset_engine_port
from personas.insult.core.presets import PresetMode, PresetSelection, build_preset_prompt

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
STAGES = REPO_ROOT / "personas" / "insult" / "cogs" / "chat" / "stages.py"

_SEL_LLM = PresetSelection(mode=PresetMode.INTELLECTUAL_PRESSURE, reason="llm_pick")
_SEL_REGEX = PresetSelection(mode=PresetMode.DEFAULT_ABRASIVE, reason="fallback")


def _settings(enabled: bool, timeout_ms: int = 1500):
    return types.SimpleNamespace(
        preset_classifier_llm_enabled=enabled,
        preset_classifier_timeout_ms=timeout_ms,
        preset_classifier_model="claude-haiku-4-5-20251001",
    )


def _patch_regex(monkeypatch, sel=_SEL_REGEX):
    monkeypatch.setattr("personas.insult.composition.classify_preset", lambda *a, **k: sel)


# --- Resistance: the boundary holds at the AST level -------------------------


def test_stages_does_not_import_presets_nor_presets_llm() -> None:
    """The seam's whole point: stages consumes the engine through the port.
    The vocabulary (PresetSelection/PresetModifier) legally comes from
    insult.core.contracts — the FORBIDDEN modules are the strategy/rendering
    packages. Pins the two edges PR-E removed, even function-local."""
    tree = ast.parse(STAGES.read_text(encoding="utf-8"), filename=str(STAGES))
    offenders: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("personas.insult.core.presets"):
            offenders.append(f"line {node.lineno}: from {node.module} import ...")
        elif isinstance(node, ast.Import):
            offenders.extend(
                f"line {node.lineno}: import {a.name}"
                for a in node.names
                if a.name.startswith("personas.insult.core.presets")
            )
    assert not offenders, "stages.py reaches into presets/presets_llm again:\n" + "\n".join(offenders)


# --- resolve(): strategy arbitration ------------------------------------------


async def test_disabled_flag_resolves_via_regex(monkeypatch) -> None:
    """Positive: with the LLM middleware off, the regex classifier decides and
    the telemetry scalars say so."""
    _patch_regex(monkeypatch)
    engine = build_preset_engine_port(judge_client=None, settings=_settings(False))
    result = await engine.resolve("hola", [], [])
    assert result.selection is _SEL_REGEX
    assert result.classifier_source == "regex"
    assert result.classifier_ms == 0


async def test_llm_path_wins_when_it_answers(monkeypatch) -> None:
    """Positive: LLM enabled + fast answer → the LLM selection wins and the
    source scalar reflects it."""
    _patch_regex(monkeypatch)

    async def _fake_llm(*a, **k):
        return _SEL_LLM

    monkeypatch.setattr("personas.insult.composition.classify_preset_llm", _fake_llm)
    engine = build_preset_engine_port(judge_client=object(), settings=_settings(True))
    result = await engine.resolve("hola", [], [])
    assert result.selection is _SEL_LLM
    assert result.classifier_source == "llm"


async def test_llm_timeout_falls_back_to_regex(monkeypatch) -> None:
    """Resistance: a hung LLM classifier never blocks the turn — the engine
    times out, cancels, and the regex selection is the result."""
    _patch_regex(monkeypatch)

    async def _hung_llm(*a, **k):
        await asyncio.sleep(30)

    monkeypatch.setattr("personas.insult.composition.classify_preset_llm", _hung_llm)
    engine = build_preset_engine_port(judge_client=object(), settings=_settings(True, timeout_ms=20))
    result = await engine.resolve("hola", [], [])
    assert result.selection is _SEL_REGEX
    assert result.classifier_source == "regex"


async def test_llm_error_falls_back_to_regex(monkeypatch) -> None:
    """Resistance: an LLM-path exception never propagates — regex result."""
    _patch_regex(monkeypatch)

    async def _boom(*a, **k):
        raise RuntimeError("judge down")

    monkeypatch.setattr("personas.insult.composition.classify_preset_llm", _boom)
    engine = build_preset_engine_port(judge_client=object(), settings=_settings(True))
    result = await engine.resolve("hola", [], [])
    assert result.selection is _SEL_REGEX
    assert result.classifier_source == "regex"


# --- resolve(): rendered guidance ---------------------------------------------


async def test_guidance_block_is_rendered_preset_prompt(monkeypatch) -> None:
    """Positive: the result carries the rendered preset guidance — S3 receives
    fragments, not nouns. (Overlay positive/resistance pair lives in
    test_behavioral_guidance.py against the same engine path.)"""
    _patch_regex(monkeypatch)
    engine = build_preset_engine_port(judge_client=None, settings=_settings(False))
    result = await engine.resolve("hola", [], [])
    assert result.guidance_block == build_preset_prompt(_SEL_REGEX)
    assert result.vulnerable_overlay is False
