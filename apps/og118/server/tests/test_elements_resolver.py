"""The app-level element → runner resolver (OG118-ELEMENTS-ADR-1).

An active element swaps ONLY the persona; an unknown/blank token falls back to the
base og118 runner. Building a Runner just composes it (no LLM call), so this runs
offline.
"""

from __future__ import annotations

from app import _runner, _runner_and_element


def test_no_element_returns_base_runner() -> None:
    runner, element = _runner_and_element(None)
    assert runner is _runner
    assert element is None


def test_unknown_token_falls_back_to_base() -> None:
    runner, element = _runner_and_element("119")
    assert runner is _runner and element is None


def test_oxygen_swaps_to_the_vultur_persona() -> None:
    runner, element = _runner_and_element("oxigeno")
    assert element is not None and element.symbol == "O"
    assert runner is not _runner
    # the swapped persona is Vultur's content, not the base og118 companion
    assert "Vultur Analytica" in runner.persona
    assert "Índice de Farsa Autocomplaciente" in runner.persona


def test_element_runner_is_cached_per_id() -> None:
    a, _ = _runner_and_element("O")
    b, _ = _runner_and_element("oxigeno")  # same element, different token
    assert a is b  # one runner per element, not rebuilt each turn


def test_element_runner_keeps_the_companion_filesystem_guard() -> None:
    """A persona swap must NOT widen the tool policy — Vultur is still filesystem-blocked."""
    runner, _ = _runner_and_element("oxigeno")
    blocked = set(runner.tool_policy.builtin_disallowed)
    for tool in ("Bash", "Read", "Glob", "Write"):
        assert tool in blocked
