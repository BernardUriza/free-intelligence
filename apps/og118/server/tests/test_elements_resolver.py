"""The app-level element → runner resolver (OG118-ELEMENTS-ADR-1 + ENGINE-BINDING-ADR-1).

An unknown/blank token falls back to the base og118 runner. An EXTERNAL element
(Oxígeno → the live Vultur engine) does NOT build a local runner — chat_stream
proxies it. A LOCAL element would compose its persona and run on og118's own
runner; no active element is local today, so that build path is covered directly
via build_runner (the companion safety property must survive a persona swap).
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


def test_oxygen_binds_external_and_skips_the_local_runner() -> None:
    # Oxígeno runs on the external Vultur engine, so the resolver does NOT build a
    # local runner — it returns the base runner as an unused placeholder (the
    # chat_stream external branch ignores it) plus the element with its binding.
    runner, element = _runner_and_element("oxigeno")
    assert element is not None and element.symbol == "O"
    assert element.engine_binding is not None and element.engine_binding.is_external
    assert runner is _runner  # no per-element runner built for an external element


def test_base_runner_keeps_the_companion_filesystem_guard() -> None:
    """The base og118 runner (serves 'no element') is filesystem-blocked."""
    blocked = set(_runner.tool_policy.builtin_disallowed)
    for tool in ("Bash", "Read", "Glob", "Write"):
        assert tool in blocked


def test_a_local_persona_swap_keeps_the_companion_guard() -> None:
    """A LOCAL element composes its persona and runs on og118's runner; that swap
    must NOT widen the tool policy. No active element is local, so exercise the
    build path directly with Oxígeno's composed (SSOT) persona as the input."""
    from runner import build_runner
    from elements_registry import get_registry

    reg = get_registry()
    composed = reg.composed_persona(reg.resolve("oxigeno"))
    runner = build_runner(persona_text=composed)
    assert "Vultur Analytica" in runner.persona
    blocked = set(runner.tool_policy.builtin_disallowed)
    for tool in ("Bash", "Read", "Glob", "Write"):
        assert tool in blocked
