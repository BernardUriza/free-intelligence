"""Unit tests for the demux host's DETERMINISTIC shadow router (HOST 5/6 slice A).

The shadow router is the host's reception brain running in SHADOW mode: given a
turn's text it decides which persona the host WOULD route to, deterministically
(no LLM, no gpt-4.1 spend, no ``personas.*`` import). It never changes where the
turn actually goes — the persona pipeline logs ``current_target`` vs the shadow
``target`` so divergences are measurable before any cutover.

These tests pin the deterministic decision table. The pure function must mirror
the live routing rules in ``_stage_bind_identity`` (the ``@vultur``/``~vultur``
prefix) so a divergence in the log means a REAL routing gap, not a stale shadow.
"""

from __future__ import annotations

import pytest

from demux_ai.shadow_router import ShadowDecision, shadow_route


def test_plain_text_routes_to_insult_default() -> None:
    d = shadow_route("hola, qué opinas de esto")
    assert d == ShadowDecision(target="insult", reason="default_insult")


@pytest.mark.parametrize("prefix", ["@vultur ", "~vultur "])
def test_vultur_prefix_routes_to_vultur(prefix: str) -> None:
    d = shadow_route(f"{prefix}recomiéndame una película")
    assert d.target == "vultur"
    assert d.reason == "vultur_prefix"


def test_vultur_prefix_is_case_insensitive() -> None:
    assert shadow_route("@VULTUR dame cine").target == "vultur"


def test_vultur_substring_without_prefix_stays_insult() -> None:
    # "vultur" mentioned mid-sentence is NOT a routing prefix — only the
    # leading @vultur/~vultur token routes. Mirrors the live stage rule.
    assert shadow_route("oye insult, qué tal vultur como crítico").target == "insult"


def test_empty_text_routes_to_insult() -> None:
    assert shadow_route("").target == "insult"


def test_decision_is_frozen() -> None:
    d = shadow_route("x")
    with pytest.raises((AttributeError, Exception)):
        d.target = "vultur"  # type: ignore[misc]
