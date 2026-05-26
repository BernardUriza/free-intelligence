"""fi-core capabilities → MCP server specs.

A runner declares capabilities by name (e.g. ``["cognitive", "persona"]``);
this maps each to the :class:`~fi_runner.backend.MCPServerSpec` that spawns the
matching fi-core MCP server. Tool names are read from fi-core's zero-dep MCP
contracts when available (falling back to whole-server allow).
"""

from __future__ import annotations

import sys

from .backend import MCPServerSpec


def cognitive(*, env_passthrough: bool = True) -> MCPServerSpec:
    """The fi-core clinical cognitive-flow MCP server."""
    try:
        from fi_core.cognitive import MCP_SERVER_NAME, MCP_TOOLS  # zero-dep contract

        name, tools = MCP_SERVER_NAME, tuple(t["name"] for t in MCP_TOOLS)
    except Exception:  # noqa: BLE001 - best-effort contract read; fall back to whole-server allow
        name, tools = "fi-core-cognitive", ()
    return MCPServerSpec(
        name=name,
        command=sys.executable,
        args=["-m", "fi_core.cognitive.mcp_server"],
        tools=tools,
        env_passthrough=env_passthrough,
    )


def persona(*, env_passthrough: bool = True) -> MCPServerSpec:
    """The fi-core persona / anti-drift MCP server."""
    try:
        from fi_core.persona import MCP_SERVER_NAME, MCP_TOOLS

        name, tools = MCP_SERVER_NAME, tuple(t["name"] for t in MCP_TOOLS)
    except Exception:  # noqa: BLE001 - best-effort contract read; fall back to whole-server allow
        name, tools = "fi-core-persona", ()
    return MCPServerSpec(
        name=name,
        command=sys.executable,
        args=["-m", "fi_core.persona.mcp_server"],
        tools=tools,
        env_passthrough=env_passthrough,
    )


def rag(*, env_passthrough: bool = True) -> MCPServerSpec:
    """The fi-core retrieval MCP server (chunking + lexical/semantic search)."""
    try:
        from fi_core.rag import MCP_SERVER_NAME, MCP_TOOLS  # zero-dep contract

        name, tools = MCP_SERVER_NAME, tuple(t["name"] for t in MCP_TOOLS)
    except Exception:  # noqa: BLE001 - best-effort contract read; fall back to whole-server allow
        name, tools = "fi-core-rag", ()
    return MCPServerSpec(
        name=name,
        command=sys.executable,
        args=["-m", "fi_core.rag.mcp_server"],
        tools=tools,
        env_passthrough=env_passthrough,
    )


def rag_store(*, env_passthrough: bool = True) -> MCPServerSpec:
    """The fi-core STATEFUL retrieval MCP server — persist documents and query
    them later (ingest/search/list/delete, namespaced by corpus_id). Backend +
    path via env (FI_RAG_BACKEND, FI_RAG_STORE_PATH); lexical/zero-model default."""
    try:
        from fi_core.rag import STORE_MCP_SERVER_NAME, STORE_MCP_TOOLS  # zero-dep contract

        name, tools = STORE_MCP_SERVER_NAME, tuple(t["name"] for t in STORE_MCP_TOOLS)
    except Exception:  # noqa: BLE001 - best-effort contract read; fall back to whole-server allow
        name, tools = "fi-core-rag-store", ()
    return MCPServerSpec(
        name=name,
        command=sys.executable,
        args=["-m", "fi_core.rag.store_mcp_server"],
        tools=tools,
        env_passthrough=env_passthrough,
    )


def task_tracker(*, env_passthrough: bool = True) -> MCPServerSpec:
    """The fi-core task_tracker MCP — agent declares its plan before executing.

    Tools: ``declare_plan``, ``start_step``, ``complete_step``, ``fail_step``.
    When the runner sees these calls during streaming, it re-emits semantic
    events (``plan``, ``step_started``, ``step_done``) so UIs can paint a
    checklist instead of disconnected step rows (see ``Runner.run_stream`` +
    ``_derive_plan_events``)."""
    try:
        from fi_core.task_tracker import MCP_SERVER_NAME, MCP_TOOLS  # zero-dep contract

        name, tools = MCP_SERVER_NAME, tuple(t["name"] for t in MCP_TOOLS)
    except Exception:  # noqa: BLE001 - best-effort contract read; fall back to whole-server allow
        name, tools = "fi_core_task_tracker", ()
    return MCPServerSpec(
        name=name,
        command=sys.executable,
        args=["-m", "fi_core.task_tracker.mcp_server"],
        tools=tools,
        env_passthrough=env_passthrough,
    )


#: capability name → factory.
REGISTRY = {
    "cognitive": cognitive,
    "persona": persona,
    "rag": rag,
    "rag_store": rag_store,
    "task_tracker": task_tracker,
}


def resolve(names: list[str], *, env_passthrough: bool = True) -> list[MCPServerSpec]:
    """Resolve capability names to MCP server specs.

    ``env_passthrough`` is forwarded to every spec — a consumer that drives the
    stdio servers itself (e.g. insult, which builds options and runs its own
    pool) can set it to match its existing behavior.
    """
    specs: list[MCPServerSpec] = []
    for name in names:
        if name not in REGISTRY:
            raise KeyError(f"unknown capability {name!r}; known: {sorted(REGISTRY)}")
        specs.append(REGISTRY[name](env_passthrough=env_passthrough))
    return specs
