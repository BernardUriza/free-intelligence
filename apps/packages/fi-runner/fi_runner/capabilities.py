"""fi-core capabilities → MCP server specs.

A runner declares capabilities by name (e.g. ``["cognitive", "persona"]``);
this maps each to the :class:`~fi_runner.backend.MCPServerSpec` that spawns the
matching fi-core MCP server. Tool names are read from fi-core's zero-dep MCP
contracts when available (falling back to whole-server allow).

Every capability is the SAME SHAPE (best-effort contract read → fall back to
whole-server allow → MCPServerSpec with ``python -m <module>``), so the actual
build lives in :func:`_capability_spec` and each public factory is a one-line
configuration of the differences (module path + fallback name + contract
attribute names, where ``rag_store`` is the only outlier with ``STORE_*``
prefixed contract symbols). Adding a new capability is registering one line
in :data:`REGISTRY` and adding a one-line factory.
"""

from __future__ import annotations

import importlib
import sys
from collections.abc import Callable

from .backend import MCPServerSpec


def _capability_spec(
    *,
    server_module: str,
    contract_module: str,
    fallback_name: str,
    name_attr: str = "MCP_SERVER_NAME",
    tools_attr: str = "MCP_TOOLS",
    env_passthrough: bool = False,
) -> MCPServerSpec:
    """Build the spec for one fi-core capability.

    Best-effort reads ``(name_attr, tools_attr)`` from ``contract_module`` to
    populate the server name + tool allowlist. On any import/attribute error
    (fi-core not installed, contract changed, etc.) falls back to ``fallback_
    name`` + empty tools — which means ``mcp__<name>`` allows the whole server
    (forward-compatible: a server that adds tools mid-release still works).

    The contract module is always shallow (``fi_core.<cap>``) and dep-free —
    importing it never pulls the MCP SDK or heavy backends. The HEAVY server
    module (``server_module``, e.g. ``fi_core.cognitive.mcp_server``) is only
    ever spawned via ``python -m`` from a subprocess; we don't import it here."""
    try:
        contract = importlib.import_module(contract_module)
        name = getattr(contract, name_attr)
        tools = tuple(t["name"] for t in getattr(contract, tools_attr))
    except Exception:  # noqa: BLE001 - best-effort contract read; fall back to whole-server allow
        name, tools = fallback_name, ()
    return MCPServerSpec(
        name=name,
        command=sys.executable,
        args=["-m", server_module],
        tools=tools,
        env_passthrough=env_passthrough,
    )


def cognitive(*, env_passthrough: bool = False) -> MCPServerSpec:
    """The fi-core clinical cognitive-flow MCP server."""
    return _capability_spec(
        server_module="fi_core.cognitive.mcp_server",
        contract_module="fi_core.cognitive",
        fallback_name="fi-core-cognitive",
        env_passthrough=env_passthrough,
    )


def persona(*, env_passthrough: bool = False) -> MCPServerSpec:
    """The fi-core persona / anti-drift MCP server."""
    return _capability_spec(
        server_module="fi_core.persona.mcp_server",
        contract_module="fi_core.persona",
        fallback_name="fi-core-persona",
        env_passthrough=env_passthrough,
    )


def rag(*, env_passthrough: bool = False) -> MCPServerSpec:
    """The fi-core retrieval MCP server (chunking + lexical/semantic search)."""
    return _capability_spec(
        server_module="fi_core.rag.mcp_server",
        contract_module="fi_core.rag",
        fallback_name="fi-core-rag",
        env_passthrough=env_passthrough,
    )


def rag_store(*, env_passthrough: bool = False) -> MCPServerSpec:
    """The fi-core STATEFUL retrieval MCP server — persist documents and query
    them later (ingest/search/list/delete, namespaced by corpus_id). Backend +
    path via env (FI_RAG_BACKEND, FI_RAG_STORE_PATH); lexical/zero-model default.

    Outlier: the ``rag`` module also hosts the stateless server, so the stateful
    one's contract symbols are prefixed (``STORE_MCP_SERVER_NAME``,
    ``STORE_MCP_TOOLS``) to coexist in the same namespace."""
    return _capability_spec(
        server_module="fi_core.rag.store_mcp_server",
        contract_module="fi_core.rag",
        fallback_name="fi-core-rag-store",
        name_attr="STORE_MCP_SERVER_NAME",
        tools_attr="STORE_MCP_TOOLS",
        env_passthrough=env_passthrough,
    )


def task_tracker(*, env_passthrough: bool = False) -> MCPServerSpec:
    """The fi-core task_tracker MCP — agent declares its plan before executing.

    Tools: ``declare_plan``, ``start_step``, ``complete_step``, ``fail_step``.
    When the runner sees these calls during streaming, it re-emits semantic
    events (``plan``, ``step_started``, ``step_done``) so UIs can paint a
    checklist instead of disconnected step rows (see ``Runner.run_stream`` +
    ``_derive_plan_events``)."""
    return _capability_spec(
        server_module="fi_core.task_tracker.mcp_server",
        contract_module="fi_core.task_tracker",
        fallback_name="fi_core_task_tracker",
        env_passthrough=env_passthrough,
    )


#: capability name → factory.
REGISTRY: dict[str, Callable[..., MCPServerSpec]] = {
    "cognitive": cognitive,
    "persona": persona,
    "rag": rag,
    "rag_store": rag_store,
    "task_tracker": task_tracker,
}


def resolve(names: list[str], *, env_passthrough: bool = False) -> list[MCPServerSpec]:
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
