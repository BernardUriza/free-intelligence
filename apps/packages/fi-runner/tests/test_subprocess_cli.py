"""Tests for SubprocessCLIBackend — the generic CLI lifecycle ONLY.

The base owns spawn → raw stdout → child parses, plus the session_id template.
It promises nothing about output shape. Tests use real tiny binaries (printf,
false) so the actual subprocess path is exercised offline — no mocking.
"""

from __future__ import annotations

import pytest

from fi_runner import BackendError, SubprocessCLIBackend, ToolPolicy, TurnResult


class _PrintfCLI(SubprocessCLIBackend):
    """Concrete CLI over `printf`: echoes user_message; stdout is plain text, so
    _parse_output proves the base makes NO output-shape assumption."""

    def __init__(self, binary: str = "printf") -> None:
        self._binary = binary
        self.seen_session: str | None = None

    def _cli_binary(self) -> str:
        return self._binary

    def _not_found_message(self) -> str:
        return f"need {self._binary}"

    def _build_argv(self, *, user_message, session_id=None, **_kw) -> list[str]:  # noqa: ANN001, ANN003
        self.seen_session = session_id
        return [self._binary, user_message]

    def _parse_output(self, stdout: str) -> TurnResult:
        return TurnResult(text=stdout)


async def _run(cli: SubprocessCLIBackend, msg: str = "x", **kw) -> TurnResult:
    return await cli.run_turn(
        system_prompt="s", user_message=msg, mcp_servers=[], tool_policy=ToolPolicy(), **kw
    )


@pytest.mark.asyncio
async def test_real_spawn_returns_raw_stdout_to_child():
    # printf prints user_message verbatim (no trailing newline) → base hands the
    # raw text to _parse_output, which makes the TurnResult.
    result = await _run(_PrintfCLI(), "hola-mundo")
    assert result.text == "hola-mundo"


@pytest.mark.asyncio
async def test_nonzero_exit_raises_backend_error():
    class _FalseCLI(_PrintfCLI):
        def _build_argv(self, **_kw) -> list[str]:  # noqa: ANN003
            return ["false"]  # exits 1, empty stderr

    with pytest.raises(BackendError, match="false failed"):
        await _run(_FalseCLI())


@pytest.mark.asyncio
async def test_missing_binary_raises_backend_error_with_hint():
    with pytest.raises(BackendError, match="need definitely-not-real-xyz"):
        await _run(_PrintfCLI(binary="definitely-not-real-xyz"))


@pytest.mark.asyncio
async def test_session_id_is_threaded_to_build_argv():
    # The base's capability: session_id reaches argv construction (resume is the
    # child's flag). Threaded on resume turns, None on fresh ones.
    cli = _PrintfCLI()
    await _run(cli, session_id="sess-1")
    assert cli.seen_session == "sess-1"
    await _run(cli)
    assert cli.seen_session is None


def test_abstract_base_cannot_be_instantiated():
    with pytest.raises(TypeError):
        SubprocessCLIBackend()  # type: ignore[abstract]
