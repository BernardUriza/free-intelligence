"""SubprocessCLIBackend — a base for agent backends that drive a CLI binary.

The base owns ONLY the irreducibly generic subprocess lifecycle:
  1. check the binary is on PATH (else :class:`BackendError`),
  2. spawn it + await it,
  3. fail loudly on a non-zero exit (:class:`BackendError`),
  4. decode stdout and hand the RAW text to the child.

It promises NOTHING about the output shape — a generic CLI is not JSONL, not
line-oriented, nothing. The child's ``_parse_output`` decides how to read it.

It also owns the session-continuity TEMPLATE: ``session_id`` is threaded into
``_build_argv`` so a CLI that can resume builds a resume invocation; the returned
``TurnResult.session_id`` is the continuity handle the caller passes back. The
RESUME FLAG itself (e.g. ``codex exec resume <id>``) is the child's business.

What is decidedly NOT here (it would leak a specific harness into the base): the
argv shape, the output schema (JSONL/whatever), provider/sandbox mapping. Those
live in the concrete backend. A second CLI harness (gemini-cli, aider, ...) is
the four hooks below, not another copy of the spawn dance.
"""

from __future__ import annotations

import asyncio
import os
import shutil
from abc import ABC, abstractmethod

from ..backend import BackendError, MCPServerSpec, ToolPolicy, TurnResult


class SubprocessCLIBackend(ABC):
    """AgentBackend base for CLI-driven harnesses: spawn → raw stdout → child parses.

    Satisfies the :class:`~fi_runner.backend.AgentBackend` port; subclasses do
    NOT override :meth:`run_turn`, only the four hooks below.
    """

    async def run_turn(
        self,
        *,
        system_prompt: str,
        user_message: str,
        mcp_servers: list[MCPServerSpec],
        tool_policy: ToolPolicy,
        model: str | None = None,
        session_id: str | None = None,
    ) -> TurnResult:
        binary = self._cli_binary()
        if shutil.which(binary) is None:
            raise BackendError(self._not_found_message())
        # session_id is threaded to argv construction — a resume-capable child
        # turns it into a resume invocation; others ignore it.
        argv = self._build_argv(
            system_prompt=system_prompt,
            user_message=user_message,
            mcp_servers=mcp_servers,
            tool_policy=tool_policy,
            model=model,
            session_id=session_id,
        )
        stdout = await self._run_cli(argv)
        return self._parse_output(stdout)

    async def _run_cli(self, argv: list[str]) -> str:
        """Spawn the CLI, await it, fail on a non-zero exit, return decoded stdout.
        Raw text only — interpreting it is the child's ``_parse_output``."""
        proc = await asyncio.create_subprocess_exec(
            *argv,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=self._subprocess_env(),
        )
        out, err = await proc.communicate()
        if proc.returncode != 0:
            raise BackendError(f"{argv[0]} failed (exit {proc.returncode}): {err.decode()[:500]}")
        return out.decode()

    def _subprocess_env(self) -> dict[str, str]:
        """Environment for the child process (default: inherit the parent's)."""
        return os.environ.copy()

    # --- hooks a concrete CLI backend implements ----------------------------

    @abstractmethod
    def _cli_binary(self) -> str:
        """The executable name to look up on PATH (e.g. ``"codex"``)."""

    @abstractmethod
    def _not_found_message(self) -> str:
        """The error raised when the binary isn't on PATH (with an install hint)."""

    @abstractmethod
    def _build_argv(
        self,
        *,
        system_prompt: str,
        user_message: str,
        mcp_servers: list[MCPServerSpec],
        tool_policy: ToolPolicy,
        model: str | None,
        session_id: str | None = None,
    ) -> list[str]:
        """Build the full argv for one turn. When ``session_id`` is given AND the
        backend supports resume, build a resume invocation; otherwise a fresh one."""

    @abstractmethod
    def _parse_output(self, stdout: str) -> TurnResult:
        """Interpret the CLI's raw stdout into a :class:`TurnResult` (the child
        owns the output schema — JSONL, JSON blob, plain text, whatever)."""


__all__ = ["SubprocessCLIBackend"]
