"""The `builtins` field (#37): a turn may NARROW its mode's builtin tools, never
widen them. The consumer that asked first is the PR gatekeeper: an agent turn
with Read, Glob and Grep only — no Write, and no WebFetch to carry code out."""

import pytest
from fastapi import HTTPException

from aire.engine import MODES, TurnSpec
from aire.engine.modes import BUILTINS, policy_for
from aire.engine.options import build_options
from aire.intake import safe_builtins, safe_spec

READERS = ["Read", "Glob", "Grep"]


def _options(tmp_path, spec):
    return build_options(object(), "proj", str(tmp_path), "u" * 8, spec, resuming=False)


@pytest.mark.parametrize("mode", ["complete", "agent"])
def test_no_field_keeps_the_notch_byte_identical(tmp_path, mode):
    options = _options(tmp_path, safe_spec({"mode": mode}))
    assert options.allowed_tools == MODES[mode]["allowed_tools"]
    assert options.disallowed_tools == MODES[mode]["disallowed_tools"]
    assert options.permission_mode == MODES[mode]["permission_mode"]


def test_the_gatekeeper_subset_reads_and_nothing_else(tmp_path):
    spec = safe_spec({"mode": "agent", "builtins": ["Grep", "Read", "Glob", "Read"]})
    options = _options(tmp_path, spec)
    assert options.allowed_tools == READERS
    assert set(options.disallowed_tools) == set(BUILTINS) - set(READERS)
    assert options.permission_mode == "default", "no Write granted, so nothing auto-approves edits"


def test_keeping_write_keeps_accept_edits_and_edit():
    policy = policy_for("agent", ("Read", "Write"))
    assert policy["permission_mode"] == "acceptEdits"
    assert "Edit" not in policy["disallowed_tools"]
    assert {"WebFetch", "WebSearch", "Bash"} <= set(policy["disallowed_tools"])


def test_an_empty_list_grants_no_builtin():
    policy = policy_for("agent", ())
    assert policy["allowed_tools"] == [] and policy["disallowed_tools"] == list(BUILTINS)


@pytest.mark.parametrize("mode,raw", [
    ("agent", ["Bash"]), ("agent", ["Edit"]), ("agent", ["Read", "NotebookEdit"]),
    ("complete", ["Read"]), ("complete", ["WebSearch"]),
    ("agent", "Read"), ("agent", [7]), ("agent", {"Read": True}),
])
def test_the_wire_can_never_widen_the_notch(mode, raw):
    with pytest.raises(HTTPException) as exc:
        safe_builtins(raw, mode, "claude")
    assert exc.value.status_code == 422


def test_an_acp_agent_cannot_honour_a_subset_so_it_is_refused():
    with pytest.raises(HTTPException) as exc:
        safe_builtins(READERS, "agent", "some-acp-agent")
    assert exc.value.status_code == 422
    assert safe_builtins(None, "agent", "some-acp-agent") is None


def test_registry_tools_still_ride_beside_a_subset(tmp_path):
    spec = TurnSpec(mode="agent", tools=("persona",), builtins=("Read",))
    options = _options(tmp_path, spec)
    assert options.allowed_tools == ["Read", "mcp__persona"]
    assert "persona" in options.mcp_servers


def test_a_different_subset_is_a_different_shape_so_the_client_rebinds():
    assert TurnSpec(mode="agent") != TurnSpec(mode="agent", builtins=tuple(READERS))
    assert TurnSpec(mode="agent", builtins=("Read",)) == safe_spec(
        {"mode": "agent", "builtins": ["Read"]})
