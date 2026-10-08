"""The tool-definition shape the memory tools are declared in — SDK-free.

These tools were born as ``claude_agent_sdk.tool`` definitions for the
in-process MCP server the local SDK host mounted. That host died with the
AIRE migration (backlog ``aire-engine-stage2.md``), and the ONE remaining
consumer is ``api/mcp_http.py``, which needs exactly three things per tool:
its ``name``, its ``description``+schema for ``tools/list``, and its
``handler`` for ``tools/call``. Keeping the whole Agent SDK installed for a
decorator and a four-line type mapping was the last thread holding the
dependency, so the shape lives here instead — same signature, same JSON
Schema on the wire (pinned by test against the SDK's documented conversion).
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

_PY_TO_JSON = {str: "string", int: "integer", float: "number", bool: "boolean"}


@dataclass(frozen=True)
class ToolDef:
    """One MCP tool: the wire identity plus the coroutine that serves it."""

    name: str
    description: str
    input_schema: dict[str, Any]
    handler: Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]


def tool(
    name: str, description: str, input_schema: dict[str, Any]
) -> Callable[[Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]], ToolDef]:
    """Declare an MCP tool — the same call shape ``claude_agent_sdk.tool`` had,
    restricted to the schema form this repo actually uses (a plain
    ``{param: type}`` dict, or a ready JSON Schema object)."""

    def decorator(handler: Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]) -> ToolDef:
        return ToolDef(name=name, description=description, input_schema=input_schema, handler=handler)

    return decorator


def build_input_schema(tool_def: ToolDef) -> dict[str, Any]:
    """The JSON Schema ``tools/list`` advertises — byte-compatible with what the
    SDK's ``_build_input_schema`` produced for these tools: a ready JSON Schema
    passes through; a ``{param: type}`` dict maps types and requires every key."""
    schema = tool_def.input_schema
    if "type" in schema and "properties" in schema and isinstance(schema["type"], str):
        return schema
    properties = {name: {"type": _PY_TO_JSON.get(py_type, "string")} for name, py_type in schema.items()}
    return {"type": "object", "properties": properties, "required": list(properties)}
