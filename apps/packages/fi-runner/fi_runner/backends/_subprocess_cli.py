"""SubprocessCLIBackend — a base for agent backends that drive a CLI binary.

CodexBackend (``codex exec --json``) is the first. The irreducibly imperative
plumbing — check the binary is on PATH, spawn it, await it, fail loudly on a
non-zero exit, and parse its JSONL stdout into events — is written ONCE here. A
concrete CLI backend supplies only what actually varies via four small hooks:
the binary name + a not-found hint, how to BUILD the argv from a turn, and how to
PARSE the events into a :class:`TurnResult`. A second CLI harness (gemini-cli,
aider, ...) becomes those hooks, not another copy of the subprocess dance.

This is the HARNESS axis. The PROVIDER axis (which OpenAI-compatible API the CLI
talks to) is already declarative — see CodexBackend's ``ProviderConfig``.
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
from abc import ABC, abstractmethod
from typing import Any

from ..backend import MCPServerSpec, ToolPolicy, TurnResult


class SubprocessCLIBackend(ABC):
    """AgentBackend base for CLI-driven harnesses: spawn → JSONL → TurnResult.

    Satisfies the :class:`~fi_runner.backend.AgentBackend` port; subclasses do
    NOT override :meth:`run_turn`, only the four hooks below. Session continuity
    (``session_id``) is a per-backend concern — a CLI that supports resume can
    extend ``run_turn``; the base runs each turn one-shot.
    """

    async def run_turn(
        self,
        *,
        system_prompt: str,
        user_message: str,
        mcp_servers: list[MCPServerSpec],
        tool_policy: ToolPolicy,
        model: str | None = None,
        session_id: str | None = None,  # noqa: ARG002 - resume is a per-backend concern
    ) -> TurnResult:
        binary = self._cli_binary()
        if shutil.which(binary) is None:
            raise RuntimeError(self._not_found_message())
        argv = self._build_argv(
            system_prompt=system_prompt,
            user_message=user_message,
            mcp_servers=mcp_servers,
            tool_policy=tool_policy,
            model=model,
        )
        events = await self._run_cli(argv)
        return self._parse_events(events)

    async def _run_cli(self, argv: list[str]) -> list[dict[str, Any]]:
        """Spawn the CLI, await it, fail on a non-zero exit, parse JSONL stdout."""
        proc = await asyncio.create_subprocess_exec(
            *argv,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=self._subprocess_env(),
        )
        out, err = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(f"{argv[0]} failed (exit {proc.returncode}): {err.decode()[:500]}")
        return self._parse_jsonl(out.decode())

    @staticmethod
    def _parse_jsonl(text: str) -> list[dict[str, Any]]:
        """One JSON object per non-blank line; silently skip unparseable lines."""
        events: list[dict[str, Any]] = []
        for raw in text.splitlines():
            line = raw.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return events

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
    ) -> list[str]:
        """Build the full argv for one turn."""

    @abstractmethod
    def _parse_events(self, events: list[dict[str, Any]]) -> TurnResult:
        """Turn the parsed JSONL events into a :class:`TurnResult`."""


__all__ = ["SubprocessCLIBackend"]
