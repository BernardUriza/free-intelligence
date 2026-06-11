"""PR-F S1bPolicyPort — positive (delegation/parity) + resistance (boundary).

S1b seam (`.claude/plans/s1b_ground_truth.md`): the pipeline composes the
behavioral policy layer (adaptive prompt + 4-flow analysis + flow guidance +
extra layers) through the ``S1bPolicyPort`` Protocol
(``insult/cogs/chat/capability_ports.py``) — a finished ``PolicyBundle`` in,
zero knowledge of ``insult.core.flows`` and of the pre-LLM half of
``insult.core.character``. The adapter in ``insult.composition`` is built
WITH the host-owned ``ExpressionHistory``.

Each behavior gets a positive case AND a resistance case per
.claude/rules/robustness.md.
"""

from __future__ import annotations

import ast
from pathlib import Path

from insult.composition import build_s1b_policy_port
from insult.core.contracts.history import ExpressionHistory

REPO_ROOT = Path(__file__).resolve().parent.parent
STAGES = REPO_ROOT / "insult" / "cogs" / "chat" / "stages.py"

# The ONLY character symbols stages may still import — the post-LLM S4
# mutation half that PR-G (OutputMutationPort) will remove. Anything beyond
# this allowlist re-opens the pre-LLM coupling PR-F just closed.
_S4_CHARACTER_ALLOWLIST = {
    "MutationStage",
    "deduplicate_opener",
    "enforce_length_variation",
    "preserve_react_markers",
    "strip_echoed_quotes",
    "run_pipeline",
}


def _parse_stages() -> ast.Module:
    return ast.parse(STAGES.read_text(encoding="utf-8"), filename=str(STAGES))


# --- Resistance: the boundary holds at the AST level -------------------------


def test_stages_does_not_import_flows() -> None:
    """The seam's whole point: stages consumes flow analysis/guidance through
    the port and never reaches into ``insult.core.flows`` — not even via a
    function-local import (the module-level ratchet in
    test_arch_import_boundaries also catches it, but this pins the specific
    edge PR-F removed)."""
    offenders: list[str] = []
    for node in ast.walk(_parse_stages()):
        if isinstance(node, ast.ImportFrom) and node.module and "core.flows" in node.module:
            offenders.append(f"line {node.lineno}: from {node.module} import ...")
        elif isinstance(node, ast.Import):
            offenders.extend(f"line {node.lineno}: import {a.name}" for a in node.names if "core.flows" in a.name)
    assert not offenders, "stages.py reaches into insult.core.flows again:\n" + "\n".join(offenders)


def test_stages_character_imports_are_s4_only() -> None:
    """Resistance pin for the surviving half-edge: until PR-G lands, stages
    may import ONLY the S4 mutation symbols from ``insult.core.character``.
    Re-importing a prompt builder (``build_adaptive_prompt``,
    ``compose_extra_layers``, ``_format_other_people_block``, …) would
    silently undo PR-F without moving the ratchet."""
    offenders: list[str] = []
    for node in ast.walk(_parse_stages()):
        if isinstance(node, ast.ImportFrom) and node.module and "core.character" in node.module:
            offenders.extend(
                f"line {node.lineno}: {a.name}" for a in node.names if a.name not in _S4_CHARACTER_ALLOWLIST
            )
    assert not offenders, "stages.py imports non-S4 character symbols:\n" + "\n".join(offenders)


# --- compose(): delegation parity with the core builders ---------------------


def _compose_kwargs(**overrides) -> dict:
    base = {
        "base_prompt": "Eres Insult. Persona base de prueba.",
        "profile": None,
        "context_len": 3,
        "preset": None,  # filled by the test
        "text": "explícame por qué mi refactor no es sobreingeniería",
        "recent": [],
        "user_facts": [],
        "context_key": "chan1:user1",
        "server_pulse": "",
        "recent_response_lengths": [],
        "arc_block": "## Arc\nfase de prueba",
        "stance_block": "## Stances\npostura de prueba",
        "facts_block": "## Facts\nhecho de prueba",
        "other_participants_facts": None,
        "serenityops_snapshot": None,
        "serenityops_user_name": "tester",
    }
    base.update(overrides)
    return base


def _make_selection():
    from insult.core.presets import classify_preset

    return classify_preset("explícame por qué mi refactor no es sobreingeniería", [], [])


def test_compose_returns_full_bundle() -> None:
    """Positive: one compose() call yields the composed system prompt with
    every supplied layer embedded, the flow guidance rendered ONCE from the
    bundle's own analysis, and the preset passed through unchanged."""
    from insult.core.flows import build_flow_prompt

    selection = _make_selection()
    port = build_s1b_policy_port(ExpressionHistory())
    bundle = port.compose(**_compose_kwargs(preset=selection))

    # Preset passthrough: build_adaptive_prompt only classifies when None.
    assert bundle.preset is selection

    # The supplied pre-rendered blocks are embedded verbatim.
    for block in ("## Arc\nfase de prueba", "## Stances\npostura de prueba", "## Facts\nhecho de prueba"):
        assert block in bundle.system_prompt

    # Flow guidance is rendered from the bundle's own analysis (single
    # render, both paths consume the same string) and embedded.
    assert bundle.flow_guidance == build_flow_prompt(bundle.flow_analysis)
    if bundle.flow_guidance:
        assert bundle.flow_guidance in bundle.system_prompt

    # The persona base opens the prompt (cache-boundary contract).
    assert bundle.system_prompt.startswith("Eres Insult.")


def test_compose_skips_empty_layers() -> None:
    """Resistance: empty blocks must not leave blank-layer artifacts —
    compose_extra_layers skips falsy blocks; headers from OTHER layers must
    not appear when their block is empty."""
    selection = _make_selection()
    port = build_s1b_policy_port(ExpressionHistory())
    bundle = port.compose(**_compose_kwargs(preset=selection, arc_block="", stance_block="", facts_block=""))
    assert "## Arc" not in bundle.system_prompt
    assert "## Stances" not in bundle.system_prompt
    assert "## Facts\nhecho" not in bundle.system_prompt


# --- other_people_block(): the private reach, now behind the port ------------


def test_other_people_block_delegates_to_core_renderer() -> None:
    """Positive: same render as the core formatter (the S2 path consumes the
    port, never the private symbol)."""
    from insult.core.character.prompts import _format_other_people_block

    facts = {"Alex": [{"fact": "Su cumpleaños es el 11 de junio", "category": "identity"}]}
    port = build_s1b_policy_port(ExpressionHistory())
    assert port.other_people_block(facts) == _format_other_people_block(facts)
    assert "Alex" in port.other_people_block(facts)


# --- assess facets: S5 telemetry parity --------------------------------------


def test_assess_facets_match_core_validators() -> None:
    """Positive: the S5 facet returns exactly what the core validators return
    for the same inputs (pure functions — parity is deterministic)."""
    from insult.core.flows import detect_lifelessness, validate_flow_adherence

    selection = _make_selection()
    port = build_s1b_policy_port(ExpressionHistory())
    bundle = port.compose(**_compose_kwargs(preset=selection))

    response = "Mira, tu refactor tiene un problema concreto: el puerto hace dos cosas. ¿Cuál de las dos te importa?"
    assert port.assess_adherence(response, bundle.flow_analysis) == validate_flow_adherence(
        response, bundle.flow_analysis
    )
    assert port.assess_lifelessness(response, "explícame") == detect_lifelessness(response, "explícame")
