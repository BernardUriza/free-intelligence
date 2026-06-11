"""PR-G OutputMutationPort — positive (parity) + resistance (boundary).

Fourth capability seam (`.claude/plans/s1b_ground_truth.md`, sección
multi-PR): the pipeline mutates post-LLM text through the
``OutputMutationPort`` Protocol — raw model text in, deliverable text out.
The pipeline order + shrink guardrails are internal policy of the adapter in
``insult.composition``. The ``[REACT:]``/``[REMEMBER:]`` parsers stay
host-side in the stage.

Each behavior gets a positive case AND a resistance case per
.claude/rules/robustness.md.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from insult.composition import default_output_mutation_port

REPO_ROOT = Path(__file__).resolve().parent.parent
STAGES = REPO_ROOT / "insult" / "cogs" / "chat" / "stages.py"

pytestmark = pytest.mark.asyncio


# --- Resistance: the boundary holds at the AST level -------------------------


def test_stages_does_not_import_character_at_all() -> None:
    """PR-G closes the LAST half of the edge: stages must not touch
    ``insult.core.character`` in any form — module-level, function-local,
    bare import. (The ratchet in test_arch_import_boundaries also enforces
    it; this pins the specific edge so a regression names PR-G.)"""
    offenders: list[str] = []
    for node in ast.walk(ast.parse(STAGES.read_text(encoding="utf-8"), filename=str(STAGES))):
        if isinstance(node, ast.ImportFrom) and node.module and "core.character" in node.module:
            offenders.append(f"line {node.lineno}: from {node.module} import ...")
        elif isinstance(node, ast.Import):
            offenders.extend(f"line {node.lineno}: import {a.name}" for a in node.names if "core.character" in a.name)
    assert not offenders, "stages.py reaches into insult.core.character again:\n" + "\n".join(offenders)


# --- mutate(): parity with the inline pipeline it replaced -------------------


async def test_mutate_strips_markers_and_preserves_text() -> None:
    """Positive: marker stripping still happens inside the chain — the
    visible text loses [REACT:]/[REMEMBER:] but keeps the content."""
    port = default_output_mutation_port()
    raw = "Tu argumento se cae solo y lo sabes. [REACT:👀] [REMEMBER: Bernard odia los lunes]"
    out = await port.mutate(raw, user_text="opina", recent_response_lengths=[], recent_openers=[])
    assert "[REACT:" not in out
    assert "[REMEMBER:" not in out
    assert "Tu argumento se cae solo" in out


async def test_mutate_shrink_guardrail_skips_aggressive_echo_strip() -> None:
    """Resistance: when the echo-strip would eat >30% of the response, the
    ``max_shrink_pct`` guardrail SKIPS the stage through the port exactly as
    it did inline — the text survives intact (modulo later marker strips)."""
    user = "mi código es perfecto y no necesita tests"
    raw = "mi código es perfecto y no necesita tests — eso dijiste, y es mentira."
    port = default_output_mutation_port()
    out = await port.mutate(raw, user_text=user, recent_response_lengths=[], recent_openers=[])
    assert out == (await _inline_reference(raw, user))
    assert out == raw  # 41% shrink > 30% cap → stage skipped, text intact


async def test_mutate_preserves_intentional_quote() -> None:
    """Resistance (robustness.md): a quote-wrapped citation is intentional
    content — the echo-strip must NOT eat it through the port either."""
    user = "su equipo no crece"
    raw = '"su equipo no crece" — eso te lo inventas tú, no yo.'
    port = default_output_mutation_port()
    out = await port.mutate(raw, user_text=user, recent_response_lengths=[], recent_openers=[])
    assert '"su equipo no crece"' in out


async def _inline_reference(raw: str, user_text: str) -> str:
    """The exact pipeline the stage ran inline pre-PR-G, for parity checks."""
    from insult.cogs.chat.reactions import strip_reactions
    from insult.cogs.chat.remembers import strip_remembers
    from insult.core.character import (
        MutationStage,
        deduplicate_opener,
        enforce_length_variation,
        preserve_react_markers,
        strip_echoed_quotes,
    )
    from insult.core.character import run_pipeline as run_character_pipeline

    return await run_character_pipeline(
        [
            MutationStage(
                name="strip_echoed_quotes",
                apply=lambda t, _ctx: strip_echoed_quotes(t, user_text),
                max_shrink_pct=0.30,
                on_violation="skip_stage",
            ),
            MutationStage(
                name="enforce_length_variation",
                apply=lambda t, _ctx: enforce_length_variation(t, []),
                max_shrink_pct=0.50,
                on_violation="skip_stage",
            ),
            MutationStage(
                name="deduplicate_opener",
                apply=lambda t, _ctx: deduplicate_opener(t, []),
                max_shrink_pct=0.30,
                must_preserve=[preserve_react_markers],
                on_violation="skip_stage",
            ),
            MutationStage(
                name="strip_reactions",
                apply=lambda t, _ctx: strip_reactions(t),
                max_shrink_pct=None,
                on_violation="skip_stage",
            ),
            MutationStage(
                name="strip_remembers",
                apply=lambda t, _ctx: strip_remembers(t),
                max_shrink_pct=None,
                on_violation="skip_stage",
            ),
        ],
        raw,
        ctx={},
    )


async def test_mutate_full_parity_with_inline_pipeline() -> None:
    """Positive: byte-for-byte parity with the pre-PR-G inline pipeline on a
    payload that exercises every stage (echo + markers + opener)."""
    user = "explícame el bug"
    raw = "Mira, el bug es tuyo. [REACT:🔥] No del framework. [REMEMBER: Bernard culpa al framework]"
    port = default_output_mutation_port()
    via_port = await port.mutate(raw, user_text=user, recent_response_lengths=[], recent_openers=[])
    assert via_port == await _inline_reference(raw, user)
