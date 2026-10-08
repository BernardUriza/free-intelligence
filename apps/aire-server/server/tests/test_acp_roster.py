"""AIRE_ACP_AGENTS: the operator names what an ACP provider runs. The wire only
ever picks a name (`safe_provider`); a malformed roster is the operator's error
and says so, never a caller's 422."""

import json

import pytest
from fastapi import HTTPException

from aire.agent_sdk import UnknownProvider, backend_for
from aire.agent_sdk.acp_roster import BadRoster, roster
from aire.intake import safe_provider


def test_an_unset_roster_leaves_only_the_native_backend(monkeypatch):
    monkeypatch.delenv("AIRE_ACP_AGENTS", raising=False)
    assert roster() == {}
    assert safe_provider(None) == "claude" and safe_provider("") == "claude"
    with pytest.raises(HTTPException) as exc:
        safe_provider("qwen")
    assert exc.value.status_code == 422 and "available" in exc.value.detail
    with pytest.raises(UnknownProvider):
        backend_for("qwen")


def test_a_list_is_a_command_and_a_dict_carries_env(monkeypatch):
    monkeypatch.setenv("AIRE_ACP_AGENTS", json.dumps(
        {"qwen": ["qwen", "--acp"], "claude-acp": {"command": ["claude-code-acp"], "env": {"A": "1"}}}))
    agents = roster()
    assert agents["qwen"].command == ("qwen", "--acp") and agents["qwen"].env == {}
    assert agents["claude-acp"].env == {"A": "1"}
    assert safe_provider("qwen") == "qwen"
    assert backend_for("claude-acp").__name__.endswith("acp")


@pytest.mark.parametrize("raw", [
    "not json", "[]", json.dumps({"claude": ["x"]}), json.dumps({"bad name!": ["x"]}),
    json.dumps({"q": []}), json.dumps({"q": {"command": "qwen"}}),
    json.dumps({"q": {"command": ["qwen"], "env": {"A": 1}}}),
])
def test_a_malformed_roster_is_loud(monkeypatch, raw):
    monkeypatch.setenv("AIRE_ACP_AGENTS", raw)
    with pytest.raises(BadRoster):
        roster()
