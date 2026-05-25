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

    def __init__(
        self,
        default_model: str | None = None,
        default_sandbox: str = "read-only",
        *,
        azure_endpoint: str | None = None,
        azure_api_key_env: str = "AZURE_OPENAI_API_KEY",
        azure_wire_api: str = "responses",
    ) -> None:
        self.default_model = default_model
        self.default_sandbox = default_sandbox
        # When azure_endpoint is set, Codex is pointed at an Azure OpenAI
        # deployment (official MS support) — no ChatGPT subscription, just the
        # API key in `azure_api_key_env`. Reuse your existing AZURE_OPENAI_*.
        # Codex works with general models (gpt-4o/gpt-4.1), not only codex/
        # reasoning ones — for a chat/companion runner (alice) a general model
        # is the right call. `wire_api` defaults to "responses" (the "chat"
        # wire API is deprecated in Codex); gpt-4o/gpt-4.1 are supported on the
        # Azure Responses API (legacy "gpt-4" is not — use a 4o/4.1 deployment).
        self.azure_endpoint = azure_endpoint
        self.azure_api_key_env = azure_api_key_env
        self.azure_wire_api = azure_wire_api

    def _provider_args(self) -> list[str]:
        """`-c` overrides that point Codex at an Azure OpenAI provider."""
        if not self.azure_endpoint:
            return []
        base = self.azure_endpoint.rstrip("/")
        if not base.endswith("/openai/v1"):
            base = f"{base}/openai/v1"
        return [
            "-c", "model_provider=azure",
            "-c", 'model_providers.azure.name="Azure OpenAI"',
            "-c", f'model_providers.azure.base_url="{base}"',
            "-c", f'model_providers.azure.env_key="{self.azure_api_key_env}"',
            "-c", f'model_providers.azure.wire_api="{self.azure_wire_api}"',
        ]

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
        # `--skip-git-repo-check`: the runner cwd is NOT a git repo (containerized
        # service, no working tree), and `codex exec` refuses to run outside one
        # by default ("Not inside a trusted directory and --skip-git-repo-check
        # was not specified" → exit 1). This flag lets codex run anywhere.
        argv = [
            "codex",
            "exec",
            "--json",
            "--skip-git-repo-check",
            "--sandbox",
            self._sandbox_for(tool_policy),
        ]
        argv += self._provider_args()  # Azure OpenAI provider, if configured
        chosen_model = model or self.default_model
        if chosen_model:
            argv += ["--model", chosen_model]
        argv += self._mcp_config_args(mcp_servers)
        prompt = f"{system_prompt}\n\n---\n\n{user_message}" if system_prompt else user_message
        argv.append(prompt)
        return argv

    @staticmethod
    def _extract_text(events: list[dict]) -> str:
        """Pull the assistant text out of the JSONL event stream.

        Verified against the codex exec --json schema (OpenAI docs): the final
        message is ``{"type":"item.completed","item":{"type":"agent_message",
        "text":"..."}}``. The text lives in the item, NOT the top-level type, and
        ``turn.completed`` carries only usage (no text).

        Codex RETRIES after an ``error``/``turn.failed`` (e.g. an Azure
        ``content_filter`` stream-disconnect), so a turn can contain an aborted
        partial message THEN the real one. We keep only the ``agent_message``
        items that come AFTER the last error — those belong to the successful
        attempt. No error → take them all (a legit multi-part answer).
        """
        last_error_idx = -1
        for i, ev in enumerate(events):
            if ev.get("type") in ("error", "turn.failed"):
                last_error_idx = i
        parts: list[str] = []
        for ev in events[last_error_idx + 1 :]:
            if ev.get("type") != "item.completed":
                continue
            item = ev.get("item") or {}
            if item.get("type") == "agent_message":
                text = item.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "".join(parts)

    @staticmethod
    def _extract_usage(events: list[dict]) -> dict | None:
        """Token usage from the final ``turn.completed`` event, if present."""
        for ev in reversed(events):
            if ev.get("type") == "turn.completed":
                usage = ev.get("usage")
                if isinstance(usage, dict):
                    return usage
        return None

    @staticmethod
    def _extract_thread_id(events: list[dict]) -> str | None:
        """The Codex thread id (from ``thread.started``) — usable to resume."""
        for ev in events:
            if ev.get("type") == "thread.started":
                tid = ev.get("thread_id")
                if isinstance(tid, str):
                    return tid
        return None

    async def run_turn(
        self,
        *,
        system_prompt: str,
        user_message: str,
        mcp_servers: list[MCPServerSpec],
        tool_policy: ToolPolicy,
        model: str | None = None,
        session_id: str | None = None,  # noqa: ARG002 - Codex session resume is a v2 TODO
    ) -> TurnResult:
        # NOTE: codex exec can resume a previous session; wiring session_id ->
        # `codex exec resume <id>` is a v2 TODO. For now each turn is one-shot.
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
        return TurnResult(
            text=self._extract_text(events),
            raw=events,
            usage=self._extract_usage(events),
            session_id=self._extract_thread_id(events),
        )
