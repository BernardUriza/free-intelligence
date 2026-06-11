"""Behavioral guidance forwarding — runner ⇄ client ⇄ stages (v3.9.94).

Regression coverage for the 2026-05-22 "Insult muy agresivo" bug: discord-bot's
classifier picked the right tone (relational_probe + vulnerability overlay,
score 11, for a user hours out of suicidal ideation) but the runner path
discarded `system_prompt`, so the model answered in the raw persona.md base
tone. This wires the classifier's decision back into the turn.

Each behavior gets a positive case AND a resistance case (the near-miss that
must NOT trigger the new path) per .claude/rules/robustness.md.
"""

from __future__ import annotations

import types

import httpx
import pytest

from insult.agent.runner import _frame_turn_text
from insult.core.llm.agent_client import AgentRunnerClient
from insult.core.presets import (
    PresetMode,
    PresetSelection,
    build_preset_prompt,
    build_vulnerable_overlay_prompt,
)

# --- _frame_turn_text: the runner-side injection ---------------------------


def test_frame_includes_guidance_block_when_present():
    out = _frame_turn_text(
        channel_id="C1",
        user_id="U1",
        user_text="hola",
        behavioral_guidance="SE SUAVE: usuario vulnerable",
    )
    assert "<behavioral_guidance>\nSE SUAVE: usuario vulnerable\n</behavioral_guidance>" in out
    # guidance comes BEFORE the user text (how-to before what-to)
    assert out.index("behavioral_guidance") < out.index("hola")
    # turn_context still first
    assert out.index("turn_context") < out.index("behavioral_guidance")


def test_frame_omits_block_when_no_guidance_is_byte_identical_to_legacy():
    """Resistance case: no guidance → exactly the pre-v3.9.94 framing, no
    stray <behavioral_guidance> tag, no extra blank lines."""
    out = _frame_turn_text(channel_id="C1", user_id="U1", user_text="hola")
    assert "behavioral_guidance" not in out
    assert out == "<turn_context>\nchannel_id: C1\nuser_id: U1\n</turn_context>\n\nhola"


def test_frame_empty_string_guidance_treated_as_absent():
    """Resistance case: empty-string guidance is falsy → no block emitted."""
    out = _frame_turn_text(channel_id="C1", user_id="U1", user_text="hola", behavioral_guidance="")
    assert "behavioral_guidance" not in out


# --- AgentRunnerClient.chat: the payload forwarding ------------------------


class _FakeResp:
    status_code = 200
    text = '{"text":"ok"}'

    def json(self):
        return {"text": "ok", "model": "agent-runner", "stop_reason": "end_turn"}


class _CapturingClient:
    """Captures the JSON body of the single POST chat() makes."""

    last_payload: dict | None = None

    def __init__(self, *a, **k):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def post(self, url, json=None, headers=None):
        _CapturingClient.last_payload = json
        return _FakeResp()


@pytest.fixture
def _patch_httpx(monkeypatch):
    _CapturingClient.last_payload = None
    monkeypatch.setattr(httpx, "AsyncClient", _CapturingClient)


async def test_chat_forwards_guidance_in_payload(_patch_httpx):
    client = AgentRunnerClient(runner_url="http://runner", runner_token="t")
    await client.chat(
        "ignored-system-prompt",
        [{"role": "user", "content": "qué onda"}],
        channel_id="C1",
        user_id="U1",
        behavioral_guidance="MODE: RESPECTFUL_SERIOUS",
    )
    payload = _CapturingClient.last_payload
    assert payload is not None
    assert payload["behavioral_guidance"] == "MODE: RESPECTFUL_SERIOUS"


async def test_chat_omits_guidance_key_when_none(_patch_httpx):
    """Resistance case: no guidance kwarg → key absent from payload entirely
    (not present-as-null), so the runner's `if req.behavioral_guidance` short-
    circuits exactly as before."""
    client = AgentRunnerClient(runner_url="http://runner", runner_token="t")
    await client.chat(
        "ignored",
        [{"role": "user", "content": "qué onda"}],
        channel_id="C1",
        user_id="U1",
    )
    payload = _CapturingClient.last_payload
    assert payload is not None
    assert "behavioral_guidance" not in payload


# --- _build_behavioral_guidance: the stages-side reconstruction ------------
# (Preset + overlay composition now lives in the Preset Engine adapter; here
# stages only passes the pre-rendered fragment through. The overlay
# positive/resistance pair runs against the REAL engine path via a patched
# regex classifier — same assertions, same prod reason prefix.)


def _engine_for(monkeypatch, selection: PresetSelection):
    """Preset Engine wired for the regex-only path, classifying as `selection`."""
    from insult.composition import build_preset_engine_port

    monkeypatch.setattr("insult.composition.classify_preset", lambda *a, **k: selection)
    settings = types.SimpleNamespace(preset_classifier_llm_enabled=False)
    return build_preset_engine_port(judge_client=None, settings=settings)


def _ctx(result, text: str = ""):
    """Minimal stand-in for TurnCtx: only the attrs the builder reads.

    `text` defaults to "" so the animal-liberation corpus stays off unless a
    test deliberately puts an on-topic message in.
    """
    return types.SimpleNamespace(preset=result.selection, preset_result=result, flow_analysis=None, text=text)


async def test_build_guidance_includes_preset_prompt(monkeypatch):
    from insult.cogs.chat.stages import _build_behavioral_guidance

    sel = PresetSelection(mode=PresetMode.DEFAULT_ABRASIVE, reason="fallback")
    result = await _engine_for(monkeypatch, sel).resolve("x", [], [])
    out = _build_behavioral_guidance(_ctx(result))
    assert build_preset_prompt(sel) in out


async def test_build_guidance_adds_overlay_for_vulnerable_selection(monkeypatch):
    """Positive case: a chronic-vulnerable selection (the exact reason prefix
    prod emitted, score 11) must carry the safety overlay."""
    from insult.cogs.chat.stages import _build_behavioral_guidance

    sel = PresetSelection(
        mode=PresetMode.RELATIONAL_PROBE,
        reason="chronic_nonacute_move_allowed: score=11",
    )
    result = await _engine_for(monkeypatch, sel).resolve("x", [], [])
    assert result.vulnerable_overlay is True
    out = _build_behavioral_guidance(_ctx(result))
    assert build_vulnerable_overlay_prompt() in out


async def test_build_guidance_no_overlay_for_normal_selection(monkeypatch):
    """Resistance case: an ordinary preset (non-overlay reason) must NOT drag
    in the vulnerability overlay — otherwise everyone gets crisis treatment."""
    from insult.cogs.chat.stages import _build_behavioral_guidance

    sel = PresetSelection(mode=PresetMode.PLAYFUL_ROAST, reason="humor_signals")
    result = await _engine_for(monkeypatch, sel).resolve("x", [], [])
    assert result.vulnerable_overlay is False
    out = _build_behavioral_guidance(_ctx(result))
    assert build_vulnerable_overlay_prompt() not in out
