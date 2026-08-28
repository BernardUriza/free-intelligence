"""The SDK-free tool shape must speak the same JSON Schema the SDK spoke.

`api/mcp_http.py` advertises these schemas to AIRE's SDK on `tools/list`; a
drifted conversion would silently change every remote tool's signature. The
expected objects below are pinned against what `claude_agent_sdk`'s
`_build_input_schema` produced for the exact schema forms this repo declares
(plain `{param: type}` dicts), captured before the dependency was dropped.
"""

from __future__ import annotations

from persona_runner.mcp_tools import PERSONA_MEMORY_TOOLS
from persona_runner.mcp_tools.tooldef import ToolDef, build_input_schema, tool


def _def(schema):
    @tool("t", "d", schema)
    async def t(args):
        return {}

    return t


def test_an_empty_schema_is_an_object_with_no_required_params():
    assert build_input_schema(_def({})) == {"type": "object", "properties": {}, "required": []}


def test_python_types_map_exactly_as_the_sdk_mapped_them():
    assert build_input_schema(_def({"query": str, "limit": int, "delete": bool})) == {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "limit": {"type": "integer"},
            "delete": {"type": "boolean"},
        },
        "required": ["query", "limit", "delete"],
    }


def test_a_ready_json_schema_passes_through_untouched():
    ready = {"type": "object", "properties": {"x": {"type": "string"}}, "required": []}
    assert build_input_schema(_def(ready)) is ready


def test_every_memory_tool_is_a_tooldef_with_a_wire_identity():
    assert len(PERSONA_MEMORY_TOOLS) == 10
    for t in PERSONA_MEMORY_TOOLS:
        assert isinstance(t, ToolDef)
        assert t.name and t.description
        schema = build_input_schema(t)
        assert schema["type"] == "object"
