"""ClaudeAgentOptions assembly + the capability guard that must never degrade.

Option assembly is delegated to `fi_runner` (the backend-agnostic framework):
the runner declares its MCP servers and a ToolPolicy; fi_runner builds the
allowlist, mcp_servers, cwd, setting_sources and permission mode.

The guard is the point of this module: WebSearch is LOAD-BEARING and its absence
fails SILENTLY (the agent simply never searches and deflects with banter). So a
missing built-in crashes the boot, loudly, instead of shipping a runner that
reports `healthy` while being unable to answer anything factual.
"""

from __future__ import annotations

from typing import Any

import structlog

from persona_runner.core import config

log = structlog.get_logger()

# Playwright MCP — stdio subprocess spawned by the SDK on session creation. Lets
# the agent scrape JS-heavy / social sites (IG/FB/TikTok/X) that Anthropic's
# `web_search` server tool cannot reach (no SERP coverage, JS rendering, anti-bot).
# `--isolated` keeps cookies in memory so the bot never logs in with a real
# account. `--headless` mandatory in container.
PLAYWRIGHT_SERVER_NAME = "playwright"
PLAYWRIGHT_ALLOWED_TOOLS = [
    "browser_navigate",
    "browser_snapshot",
    "browser_take_screenshot",
    "browser_wait_for",
    "browser_click",
    "browser_evaluate",
]

# Built-in Claude Code tools the runner MUST be able to call. fi_runner's
# allowlist is builtin_allowed plus the MCP tools, so an empty builtin_allowed
# (the bug found 2026-06-14) strips WebSearch with zero error. Asserted at boot
# AND per session so a regression fails LOUDLY.
REQUIRED_BUILTIN_TOOLS = ("WebSearch", "WebFetch")


def verify_required_tools(options: Any) -> None:
    """Raise loudly if the resolved allowlist is missing a required built-in.

    The guardrail against the silent capability gap: rather than ship a runner
    that boots ``healthy`` but deflects every factual question, crash with a
    clear diagnostic the moment the capability is absent.
    """
    allowed = set(getattr(options, "allowed_tools", None) or [])
    missing = [t for t in REQUIRED_BUILTIN_TOOLS if t not in allowed]
    if missing:
        log.error(
            "agent_runner_missing_required_tools",
            missing=missing,
            allowed=sorted(allowed),
        )
        raise RuntimeError(
            f"The persona runner is missing required built-in tools {missing}; "
            f"web search is load-bearing and must not degrade silently "
            f"(allowed_tools={sorted(allowed)})"
        )


async def build_options(persona: str, model: str | None = None) -> Any:
    """Construct ClaudeAgentOptions for a new session.

    MCP servers registered: the in-process `persona_memory` (Postgres tools), fi-core's
    persona server (anti-drift, resolved from fi_runner's CAPABILITY registry so
    there is no tool list to keep in sync here), and Playwright over stdio.

    `model` accepts a router decision (Haiku/Sonnet/Opus); falls back to
    DEFAULT_MODEL when None — the router-less path, so behavior is preserved when
    a caller skips routing.
    """
    from fi_runner import ClaudeCodeBackend, MCPServerSpec, PermissionMode, ToolPolicy, capabilities

    from persona_runner.mcp_tools import (
        PERSONA_MEMORY_SERVER_NAME,
        PERSONA_MEMORY_TOOLS,
        build_persona_memory_server,
    )

    specs = [
        MCPServerSpec(
            name=PERSONA_MEMORY_SERVER_NAME,
            server=build_persona_memory_server(),  # in-process MCP server
            tools=tuple(t.name for t in PERSONA_MEMORY_TOOLS),
        ),
        *capabilities.resolve(["persona"], env_passthrough=False),
        MCPServerSpec(
            name=PLAYWRIGHT_SERVER_NAME,
            command="npx",
            args=["@playwright/mcp@latest", "--headless", "--isolated"],
            tools=tuple(PLAYWRIGHT_ALLOWED_TOOLS),
            env_passthrough=False,
        ),
    ]

    backend = ClaudeCodeBackend(cwd=str(config.WORKSPACE_ROOT), setting_sources=["project"])
    options = backend.build_options(
        system_prompt=persona,
        mcp_servers=specs,
        tool_policy=ToolPolicy(
            permission_mode=PermissionMode.BYPASS,
            builtin_allowed=list(REQUIRED_BUILTIN_TOOLS),
        ),
        model=model or config.DEFAULT_MODEL,
    )
    verify_required_tools(options)
    return options
