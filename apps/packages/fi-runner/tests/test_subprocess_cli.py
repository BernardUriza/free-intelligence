"""Tests for SubprocessCLIBackend — the base CLI backends share.

The imperative plumbing (PATH check → spawn → JSONL parse) is tested without a
real binary: ``_parse_jsonl`` is pure, and a fake subclass overrides ``_run_cli``
to skip the spawn so the template flow (hooks → TurnResult) is exercised offline.
"""

from __future__ import annotations

import pytest

from fi_runner import SubprocessCLIBackend, ToolPolicy, TurnResult


class _FakeCLI(SubprocessCLIBackend):
    """Minimal concrete CLI backend; ``_run_cli`` is stubbed (no real spawn)."""

    def __init__(self, binary: str = "sh", events: list[dict] | None = None) -> None:
        self._binary = binary
        self._events = events or [{"type": "x"}]
        self.built_argv: list[str] | None = None

    def _cli_binary(self) -> str:
        return self._binary

    def _not_found_message(self) -> str:
        return f"need {self._binary}"

    def _build_argv(self, *, system_prompt, user_message, mcp_servers, tool_policy, model) -> list[str]:  # noqa: ANN001
        self.built_argv = [self._binary, "-c", user_message]
        return self.built_argv

    def _parse_events(self, events: list[dict]) -> TurnResult:
        return TurnResult(text="parsed", raw=events)

    async def _run_cli(self, argv: list[str]) -> list[dict]:  # override: skip the real subprocess
        return self._events


def test_parse_jsonl_skips_blank_and_invalid_lines():
    text = '{"a": 1}\n\n   \nnot json\n{"b": 2}\n'
    assert SubprocessCLIBackend._parse_jsonl(text) == [{"a": 1}, {"b": 2}]


@pytest.mark.asyncio
async def test_template_flow_builds_argv_then_parses_events():
    cli = _FakeCLI(events=[{"type": "turn.completed"}])
    result = await cli.run_turn(
        system_prompt="s", user_message="hola", mcp_servers=[], tool_policy=ToolPolicy()
    )
    assert cli.built_argv == ["sh", "-c", "hola"]  # _build_argv hook ran
    assert result.text == "parsed" and result.raw == [{"type": "turn.completed"}]  # _parse_events ran


@pytest.mark.asyncio
async def test_raises_with_hint_when_binary_missing():
    cli = _FakeCLI(binary="definitely-not-a-real-binary-xyz")
    with pytest.raises(RuntimeError, match="need definitely-not-a-real-binary-xyz"):
        await cli.run_turn(system_prompt="s", user_message="u", mcp_servers=[], tool_policy=ToolPolicy())


def test_abstract_base_cannot_be_instantiated():
    with pytest.raises(TypeError):
        SubprocessCLIBackend()  # type: ignore[abstract]
