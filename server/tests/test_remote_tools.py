"""The door's half of the remote-tools contract (#48): what the wire may name,
what the environment must define, and what may never leak.

A remote tool is an HTTP MCP server the CALLER hosts (the runner that owns the
credentials) and the door only wires. The registry doctrine holds — no command
ever crosses the wire — and the trust decision is the operator's: the url's
origin must sit in AIRE_REMOTE_TOOL_ORIGINS. The headers carry the caller's own
bearer to its own server, which makes them a secret in transit: nothing here may
print one, including the REBIND line that reprs the whole TurnSpec."""

import pytest
from fastapi import HTTPException

from aire.engine.contract import RemoteTool, TurnSpec
from aire.engine.options import _mount_remote_tools
from aire.intake import safe_remote_tools

ORIGIN = "https://runner.example.com"


@pytest.fixture(autouse=True)
def _allow_origin(monkeypatch):
    monkeypatch.setenv("AIRE_REMOTE_TOOL_ORIGINS", f"{ORIGIN}, https://other.example.org")


def _spec(**over):
    base = {"name": "persona_memory", "url": f"{ORIGIN}/mcp/insult-c1",
            "headers": {"Authorization": "Bearer sekret-123"}}
    base.update(over)
    return base


def test_no_remote_tools_field_costs_nothing():
    assert safe_remote_tools(None) == () and safe_remote_tools([]) == ()


def test_a_vetted_spec_passes_whole():
    (rt,) = safe_remote_tools([_spec()])
    assert rt.name == "persona_memory"
    assert rt.url == f"{ORIGIN}/mcp/insult-c1"
    assert dict(rt.headers) == {"Authorization": "Bearer sekret-123"}


def test_an_unlisted_origin_is_refused_and_named():
    with pytest.raises(HTTPException) as exc:
        safe_remote_tools([_spec(url="https://evil.example.net/mcp")])
    assert exc.value.status_code == 422
    assert "evil.example.net" in exc.value.detail


def test_the_allowlist_lives_in_the_environment(monkeypatch):
    monkeypatch.delenv("AIRE_REMOTE_TOOL_ORIGINS", raising=False)
    with pytest.raises(HTTPException):
        safe_remote_tools([_spec()])


def test_plain_https_only():
    for url in ("http://runner.example.com/mcp",  # cleartext
                "https://user:pw@runner.example.com/mcp",  # userinfo smuggling
                "ftp://runner.example.com/mcp", "not-a-url"):
        with pytest.raises(HTTPException):
            safe_remote_tools([_spec(url=url)])


def test_registry_collision_and_duplicates_are_refused():
    with pytest.raises(HTTPException):
        safe_remote_tools([_spec(name="memory")])  # the registry owns this name
    with pytest.raises(HTTPException):
        safe_remote_tools([_spec(), _spec()])


def test_bad_names_are_refused():
    for name in ("Persona", "1tool", "a b", "x" * 33, "", None, 7):
        with pytest.raises(HTTPException):
            safe_remote_tools([_spec(name=name)])


def test_header_smuggling_is_refused():
    with pytest.raises(HTTPException):
        safe_remote_tools([_spec(headers={"X-Bad": "v\r\nInjected: yes"})])
    with pytest.raises(HTTPException):
        safe_remote_tools([_spec(headers={f"H{i}": "v" for i in range(9)})])


def test_a_header_value_never_rides_an_error():
    """Every 422 this validator can raise must be safe to log verbatim."""
    for bad in ([_spec(url="https://evil.example.net/x")],
                [_spec(name="BAD")],
                [_spec(headers={"A": "sekret\nB"})]):
        with pytest.raises(HTTPException) as exc:
            safe_remote_tools(bad)
        assert "sekret" not in str(exc.value.detail)


def test_the_repr_redacts_headers_because_rebind_prints_the_spec():
    (rt,) = safe_remote_tools([_spec()])
    spec = TurnSpec(mode="agent", remote_tools=(rt,))
    assert "sekret-123" not in repr(rt)
    assert "sekret-123" not in repr(spec)
    assert "redacted" in repr(rt)


def test_different_remote_tools_change_the_spec_identity():
    """#38 rebind triggers on TurnSpec inequality; remote_tools must count."""
    a = TurnSpec(mode="agent", remote_tools=safe_remote_tools([_spec()]))
    b = TurnSpec(mode="agent")
    assert a != b


def test_mount_builds_the_sdk_http_config_and_allows_the_server():
    (rt,) = safe_remote_tools([_spec()])
    kwargs = {"allowed_tools": ["Read"], "mcp_servers": {"memory": object()}}
    _mount_remote_tools(kwargs, (rt,))
    assert kwargs["mcp_servers"]["persona_memory"] == {
        "type": "http", "url": f"{ORIGIN}/mcp/insult-c1",
        "headers": {"Authorization": "Bearer sekret-123"},
    }
    assert "mcp__persona_memory" in kwargs["allowed_tools"]
    assert "memory" in kwargs["mcp_servers"]  # the registry mount survives


def test_mount_without_remote_tools_changes_nothing():
    kwargs = {"allowed_tools": ["Read"]}
    _mount_remote_tools(kwargs, ())
    assert kwargs == {"allowed_tools": ["Read"]}


def test_headerless_spec_omits_the_headers_key():
    (rt,) = safe_remote_tools([_spec(headers=None)])
    kwargs: dict = {"allowed_tools": []}
    _mount_remote_tools(kwargs, (rt,))
    assert "headers" not in kwargs["mcp_servers"]["persona_memory"]
    assert isinstance(RemoteTool(name="x", url="https://a/b"), RemoteTool)
