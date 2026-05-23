"""CodexBackend — wraps OpenAI Codex via the headless `codex exec --json` CLI.

The OpenAI-side agent harness (counterpart to ClaudeCodeBackend): runs on a
ChatGPT subscription, brings file-edit + shell (sandboxed) + MCP. We drive the
CLI as a subprocess (the Python ``codex_app_server`` SDK is experimental and
needs a local Codex repo checkout, so the CLI is the stable path).

Mapping to the port:
- ``ToolPolicy`` → ``--sandbox`` (read-only / workspace-write / danger-full-access).
- ``MCPServerSpec`` → ``-c mcp_servers."<name>".command/.args`` config overrides.
- system_prompt → prepended to the prompt (codex exec takes a single PROMPT arg;
  persistent instructions normally live in AGENTS.md).

Caveats (Codex maturity, 2026): the ``codex`` CLI must be on PATH; ``--json`` +
active MCP servers has a known interaction bug (openai/codex#15451) — verify the
JSONL on first integration. Requires the ``codex`` extra.
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil

from ..backend import MCPServerSpec, PermissionMode, ToolPolicy, TurnResult


class CodexBackend:
    """Agent backend backed by OpenAI Codex (`codex exec --json`)."""

    def __init__(self, default_model: str | None = None, default_sandbox: str = "read-only") -> None:
        self.default_model = default_model
        self.default_sandbox = default_sandbox

    def _sandbox_for(self, tool_policy: ToolPolicy) -> str:
        """Map the ToolPolicy to a Codex sandbox policy."""
        blocked = {t.lower() for t in tool_policy.builtin_disallowed}
        # PHI / locked-down runner: no shell or file writes.
        if {"bash", "write", "edit"} & blocked:
            return "read-only"
        if tool_policy.permission_mode in (PermissionMode.ACCEPT_EDITS, PermissionMode.BYPASS):
            return "workspace-write"
        return self.default_sandbox

    def _mcp_config_args(self, mcp_servers: list[MCPServerSpec]) -> list[str]:
        """Build ``-c`` config overrides registering each MCP server."""
        args: list[str] = []
        for spec in mcp_servers:
            key = f'mcp_servers."{spec.name}"'
            args += ["-c", f'{key}.command="{spec.command}"']
            arr = "[" + ",".join(f'"{a}"' for a in spec.args) + "]"
            args += ["-c", f"{key}.args={arr}"]
        return args

    def _build_argv(
        self,
        *,
        system_prompt: str,
        user_message: str,
        mcp_servers: list[MCPServerSpec],
        tool_policy: ToolPolicy,
        model: str | None,
    ) -> list[str]:
        argv = ["codex", "exec", "--json", "--sandbox", self._sandbox_for(tool_policy)]
        chosen_model = model or self.default_model
        if chosen_model:
            argv += ["--model", chosen_model]
        argv += self._mcp_config_args(mcp_servers)
        prompt = f"{system_prompt}\n\n---\n\n{user_message}" if system_prompt else user_message
        argv.append(prompt)
        return argv

    @staticmethod
    def _extract_text(events: list[dict]) -> str:
        """Pull the assistant text out of the JSONL event stream (defensive).

        Codex emits ``item.*`` events (agent messages, reasoning, …) plus
        ``turn.completed``. Schema is still moving, so we accept any event whose
        type mentions an agent/assistant message and read common text fields.
        """
        parts: list[str] = []
        for ev in events:
            etype = str(ev.get("type", "")).lower()
            if "agent" in etype or "assistant" in etype or "message" in etype:
                item = ev.get("item", ev)
                text = item.get("text") or item.get("content") or item.get("message")
                if isinstance(text, str):
                    parts.append(text)
        if parts:
            return "".join(parts)
        # Fallback: a turn.completed carrying a final response.
        for ev in reversed(events):
            fr = ev.get("final_response") or (ev.get("turn") or {}).get("final_response")
            if isinstance(fr, str):
                return fr
        return ""

    async def run_turn(
        self,
        *,
        system_prompt: str,
        user_message: str,
        mcp_servers: list[MCPServerSpec],
        tool_policy: ToolPolicy,
        model: str | None = None,
    ) -> TurnResult:
        if shutil.which("codex") is None:
            raise RuntimeError(
                "CodexBackend requires the `codex` CLI on PATH. "
                "Install it (e.g. `npm i -g @openai/codex`) and sign in with your ChatGPT plan."
            )
        argv = self._build_argv(
            system_prompt=system_prompt,
            user_message=user_message,
            mcp_servers=mcp_servers,
            tool_policy=tool_policy,
            model=model,
        )
        proc = await asyncio.create_subprocess_exec(
            *argv,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=os.environ.copy(),
        )
        out, err = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(f"codex exec failed (exit {proc.returncode}): {err.decode()[:500]}")

        events: list[dict] = []
        for line in out.decode().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return TurnResult(text=self._extract_text(events), raw=events)
