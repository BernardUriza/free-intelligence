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

Caveats (Codex maturity, 2026): the ``codex`` CLI must be on PATH. A past bug
(openai/codex#15451, now closed) dropped ``--output-schema`` (strict structured
output) when MCP servers were active — it did NOT affect the plain ``--json``
JSONL event stream this backend parses, so MCP capabilities work fine over Codex.
Requires the ``codex`` CLI on PATH (``npm i -g @openai/codex``) — there is no
Python dependency (the ``codex`` extra is empty, kept only to document this).
"""

from __future__ import annotations

from dataclasses import dataclass

from ..backend import MCPServerSpec, PermissionMode, ToolCall, ToolPolicy, TurnResult, mcp_tool_id
from ._subprocess_cli import SubprocessCLIBackend


@dataclass(frozen=True)
class ProviderConfig:
    """An OpenAI-compatible API provider — Codex's "API motor" mode.

    Instead of a ChatGPT login, Codex can be pointed at ANY OpenAI-compatible
    endpoint via ``-c model_provider`` overrides: Azure OpenAI, OpenAI direct,
    OpenRouter, Together, a local vLLM, ... One engine (codex), one config shape,
    every provider. The API key is never passed inline — Codex reads it from
    ``env_key`` at run time (keep secrets in the environment).
    """

    # The provider id, used as the ``model_provider=<id>`` key and the
    # ``model_providers.<id>.*`` namespace (e.g. "azure", "openai", "openrouter").
    id: str
    # The API base URL Codex calls. Pass the FULL base (we don't massage it):
    # e.g. "https://<res>.openai.azure.com/openai/v1" or "https://api.openai.com/v1".
    base_url: str
    # Env var that holds the API key (Codex reads it at run time).
    env_key: str
    # Human-readable label (``model_providers.<id>.name``). Defaults to the id.
    name: str | None = None
    # "responses" (modern, default) or the deprecated "chat" wire API.
    wire_api: str = "responses"


class CodexBackend(SubprocessCLIBackend):
    """Agent backend backed by OpenAI Codex (`codex exec --json`).

    Codex runs in one of two modes depending on config:
    - **Subscription**: a ChatGPT login (no ``provider``) — the agent harness.
    - **API motor**: a :class:`ProviderConfig` (or the ``azure_endpoint``
      shortcut) points Codex at any OpenAI-compatible API — no subscription,
      just the key in the environment.
    """

    def __init__(
        self,
        default_model: str | None = None,
        default_sandbox: str = "read-only",
        *,
        provider: ProviderConfig | None = None,
        azure_endpoint: str | None = None,
        azure_api_key_env: str = "AZURE_OPENAI_API_KEY",
        azure_wire_api: str = "responses",
    ) -> None:
        self.default_model = default_model
        self.default_sandbox = default_sandbox
        # `provider` is the general path (any OpenAI-compatible endpoint). The
        # `azure_endpoint` trio is a convenience shortcut for the most common
        # case — it builds an "azure" ProviderConfig internally (see
        # `_provider_config`). Codex works with general models (gpt-4o/gpt-4.1),
        # not only codex/reasoning ones — for a chat/companion runner (alice) a
        # general model is the right call. `wire_api` defaults to "responses"
        # (the "chat" wire API is deprecated in Codex); gpt-4o/gpt-4.1 are
        # supported on the Responses API (legacy "gpt-4" is not).
        self._provider = provider
        self.azure_endpoint = azure_endpoint
        self.azure_api_key_env = azure_api_key_env
        self.azure_wire_api = azure_wire_api

    def _provider_config(self) -> ProviderConfig | None:
        """Resolve the active provider: explicit ``provider`` wins; else the
        ``azure_endpoint`` shortcut is expanded into an "azure" ProviderConfig."""
        if self._provider is not None:
            return self._provider
        if not self.azure_endpoint:
            return None
        base = self.azure_endpoint.rstrip("/")
        if not base.endswith("/openai/v1"):
            base = f"{base}/openai/v1"
        return ProviderConfig(
            id="azure",
            base_url=base,
            env_key=self.azure_api_key_env,
            name="Azure OpenAI",
            wire_api=self.azure_wire_api,
        )

    def _provider_args(self) -> list[str]:
        """`-c` overrides that point Codex at an OpenAI-compatible provider."""
        prov = self._provider_config()
        if prov is None:
            return []
        ns = f"model_providers.{prov.id}"
        return [
            "-c", f"model_provider={prov.id}",
            "-c", f'{ns}.name="{prov.name or prov.id}"',
            "-c", f'{ns}.base_url="{prov.base_url}"',
            "-c", f'{ns}.env_key="{prov.env_key}"',
            "-c", f'{ns}.wire_api="{prov.wire_api}"',
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

    @staticmethod
    def _item_is_error(item: dict) -> bool | None:
        """Best-effort tool-result status: True on a failed status / non-zero
        exit code, None (unknown) when the item carries no failure signal."""
        if item.get("status") in ("failed", "error"):
            return True
        exit_code = item.get("exit_code")
        if isinstance(exit_code, int) and exit_code != 0:
            return True
        return None

    @classmethod
    def _tool_call_from_item(cls, item: dict) -> ToolCall | None:
        """Map one ``item.completed`` item to a :class:`ToolCall`, or ``None`` if
        it isn't a tool action (e.g. agent_message, reasoning). Item shapes follow
        the codex exec --json schema (command_execution / mcp_tool_call /
        function_call / web_search / file_change)."""
        itype = item.get("type")
        is_error = cls._item_is_error(item)
        item_id = item.get("id")
        if itype == "command_execution":
            return ToolCall.make("shell", input={"command": item.get("command")}, id=item_id, is_error=is_error)
        if itype == "mcp_tool_call":
            server, tool = item.get("server"), item.get("tool")
            name = mcp_tool_id(server, tool) if server and tool else (tool or "mcp_tool")
            return ToolCall.make(name, id=item_id, is_error=is_error)
        if itype == "function_call":
            return ToolCall.make(item.get("name") or "function_call", id=item_id, is_error=is_error)
        if itype == "web_search":
            return ToolCall.make("web_search", id=item_id, is_error=is_error)
        if itype in ("file_change", "patch", "apply_patch"):
            return ToolCall.make("file_change", id=item_id, is_error=is_error)
        return None

    @classmethod
    def _extract_tool_calls(cls, events: list[dict]) -> list[ToolCall]:
        """Tool-trace from the JSONL stream: each ``item.completed`` that is a tool
        action. Like :meth:`_extract_text`, only items AFTER the last error count
        (they belong to the successful attempt after a Codex retry)."""
        last_error_idx = -1
        for i, ev in enumerate(events):
            if ev.get("type") in ("error", "turn.failed"):
                last_error_idx = i
        calls: list[ToolCall] = []
        for ev in events[last_error_idx + 1 :]:
            if ev.get("type") != "item.completed":
                continue
            tc = cls._tool_call_from_item(ev.get("item") or {})
            if tc is not None:
                calls.append(tc)
        return calls

    # --- SubprocessCLIBackend hooks -----------------------------------------
    #
    # codex exec CAN resume a previous session (`codex exec resume <id>`); wiring
    # session_id to it is a v2 TODO, so the base's one-shot run_turn is used.

    def _cli_binary(self) -> str:
        return "codex"

    def _not_found_message(self) -> str:
        return (
            "CodexBackend requires the `codex` CLI on PATH. "
            "Install it (e.g. `npm i -g @openai/codex`) and sign in with your ChatGPT plan."
        )

    def _parse_events(self, events: list[dict]) -> TurnResult:
        return TurnResult(
            text=self._extract_text(events),
            raw=events,
            usage=self._extract_usage(events),
            session_id=self._extract_thread_id(events),
            tool_calls=self._extract_tool_calls(events),
        )
