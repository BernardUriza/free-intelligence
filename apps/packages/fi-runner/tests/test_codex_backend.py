"""Unit tests for CodexBackend's SDK-free helpers (no `codex` CLI required).

Everything CodexBackend decides before it ever spawns a subprocess lives in pure
helpers: which provider `-c` overrides to emit, which sandbox a ToolPolicy maps
to, and how to parse the JSONL event stream. Those are locked down here — most
importantly the API-motor provider config and the content-filter retry bug.
"""

from __future__ import annotations

import shutil
import subprocess

import pytest

from fi_runner import CodexBackend, MCPServerSpec, PermissionMode, ProviderConfig, ToolPolicy

AZURE_ENDPOINT = "https://northcentralus.api.cognitive.microsoft.com/"
AZURE_BASE = "https://northcentralus.api.cognitive.microsoft.com/openai/v1"


# --- _provider_args: the azure shortcut stays byte-identical (alice safety) ---


def test_azure_shortcut_emits_legacy_provider_args():
    """The azure_endpoint convenience must produce EXACTLY the args alice relied
    on before generalization — any drift would silently change alice in prod."""
    backend = CodexBackend(azure_endpoint=AZURE_ENDPOINT, azure_api_key_env="AZURE_OPENAI_API_KEY")
    assert backend._provider_args() == [
        "-c", "model_provider=azure",
        "-c", 'model_providers.azure.name="Azure OpenAI"',
        "-c", f'model_providers.azure.base_url="{AZURE_BASE}"',
        "-c", 'model_providers.azure.env_key="AZURE_OPENAI_API_KEY"',
        "-c", 'model_providers.azure.wire_api="responses"',
    ]


def test_azure_shortcut_does_not_double_append_openai_v1():
    backend = CodexBackend(azure_endpoint=AZURE_BASE)  # already ends in /openai/v1
    cfg = backend._provider_config()
    assert cfg is not None
    assert cfg.base_url == AZURE_BASE  # not .../openai/v1/openai/v1


# --- _provider_args: the generic provider path -----------------------------


def test_generic_provider_emits_its_own_namespace():
    backend = CodexBackend(
        provider=ProviderConfig(
            id="openrouter",
            base_url="https://openrouter.ai/api/v1",
            env_key="OPENROUTER_API_KEY",
            name="OpenRouter",
        )
    )
    assert backend._provider_args() == [
        "-c", "model_provider=openrouter",
        "-c", 'model_providers.openrouter.name="OpenRouter"',
        "-c", 'model_providers.openrouter.base_url="https://openrouter.ai/api/v1"',
        "-c", 'model_providers.openrouter.env_key="OPENROUTER_API_KEY"',
        "-c", 'model_providers.openrouter.wire_api="responses"',
    ]


def test_provider_name_defaults_to_id():
    backend = CodexBackend(
        provider=ProviderConfig(id="openai", base_url="https://api.openai.com/v1", env_key="OPENAI_API_KEY")
    )
    args = backend._provider_args()
    assert '-c' in args
    assert 'model_providers.openai.name="openai"' in args


def test_explicit_provider_wins_over_azure_shortcut():
    backend = CodexBackend(
        provider=ProviderConfig(id="openai", base_url="https://api.openai.com/v1", env_key="OPENAI_API_KEY"),
        azure_endpoint=AZURE_ENDPOINT,
    )
    assert "model_provider=openai" in backend._provider_args()
    assert "model_provider=azure" not in backend._provider_args()


def test_no_provider_means_subscription_mode_no_args():
    """No provider + no azure_endpoint = ChatGPT login mode → no `-c` overrides."""
    assert CodexBackend()._provider_args() == []
    assert CodexBackend()._provider_config() is None


# --- _sandbox_for ----------------------------------------------------------


def test_sandbox_phi_runner_is_read_only():
    policy = ToolPolicy(builtin_disallowed=["Bash", "Write", "Edit"])
    assert CodexBackend()._sandbox_for(policy) == "read-only"


def test_sandbox_accept_edits_is_workspace_write():
    policy = ToolPolicy(permission_mode=PermissionMode.ACCEPT_EDITS)
    assert CodexBackend()._sandbox_for(policy) == "workspace-write"


def test_sandbox_default_falls_back_to_backend_default():
    backend = CodexBackend(default_sandbox="workspace-write")
    assert backend._sandbox_for(ToolPolicy()) == "workspace-write"


# --- _mcp_config_args ------------------------------------------------------


def test_mcp_config_args_builds_command_and_args_arrays():
    specs = [MCPServerSpec(name="cognitive", command="python", args=["-m", "fi_core.cognitive.mcp_server"])]
    assert CodexBackend()._mcp_config_args(specs) == [
        "-c", 'mcp_servers."cognitive".command="python"',
        "-c", 'mcp_servers."cognitive".args=["-m","fi_core.cognitive.mcp_server"]',
    ]


# --- _extract_text: THE content-filter retry regression --------------------


def test_extract_text_drops_aborted_partial_before_retry():
    """Regression for the prod bug: Azure content_filter aborts a partial, codex
    retries, and the naive parser concatenated 'I'm sorry...' + the real reply.
    Only agent_messages AFTER the last error count."""
    events = [
        {"type": "thread.started", "thread_id": "t1"},
        {"type": "turn.started"},
        {"type": "item.completed", "item": {"type": "agent_message", "text": "I'm sorry, but I cannot assist"}},
        {"type": "error", "message": "content_filter mid-stream"},
        {"type": "item.completed", "item": {"type": "agent_message", "text": "Hola, ¿cómo estás?"}},
        {"type": "turn.completed", "usage": {"input_tokens": 100, "output_tokens": 20}},
    ]
    assert CodexBackend._extract_text(events) == "Hola, ¿cómo estás?"


def test_extract_text_keeps_all_parts_when_no_error():
    events = [
        {"type": "item.completed", "item": {"type": "agent_message", "text": "part one. "}},
        {"type": "item.completed", "item": {"type": "agent_message", "text": "part two."}},
    ]
    assert CodexBackend._extract_text(events) == "part one. part two."


def test_extract_text_handles_turn_failed_as_error_boundary():
    events = [
        {"type": "item.completed", "item": {"type": "agent_message", "text": "discard me"}},
        {"type": "turn.failed"},
        {"type": "item.completed", "item": {"type": "agent_message", "text": "keep me"}},
    ]
    assert CodexBackend._extract_text(events) == "keep me"


def test_extract_text_empty_when_no_agent_message():
    assert CodexBackend._extract_text([{"type": "turn.completed", "usage": {}}]) == ""


# --- _extract_usage / _extract_thread_id -----------------------------------


def test_extract_usage_from_turn_completed():
    events = [{"type": "turn.completed", "usage": {"input_tokens": 11, "output_tokens": 5}}]
    assert CodexBackend._extract_usage(events) == {"input_tokens": 11, "output_tokens": 5}


def test_extract_usage_none_when_absent():
    assert CodexBackend._extract_usage([{"type": "turn.started"}]) is None


def test_extract_thread_id_from_thread_started():
    events = [{"type": "thread.started", "thread_id": "thread_abc"}]
    assert CodexBackend._extract_thread_id(events) == "thread_abc"


def test_extract_thread_id_none_when_absent():
    assert CodexBackend._extract_thread_id([{"type": "turn.started"}]) is None


# --- _extract_tool_calls: the tool-trace -----------------------------------


def test_extract_tool_calls_maps_item_types_and_status():
    events = [
        {"type": "thread.started", "thread_id": "t"},
        {"type": "item.completed", "item": {"type": "command_execution", "command": "ls", "exit_code": 0}},
        {"type": "item.completed", "item": {"type": "mcp_tool_call", "server": "cognitive", "tool": "assess"}},
        {"type": "item.completed", "item": {"type": "command_execution", "command": "boom", "exit_code": 2}},
        {"type": "item.completed", "item": {"type": "agent_message", "text": "done"}},  # not a tool
        {"type": "turn.completed", "usage": {}},
    ]
    calls = CodexBackend._extract_tool_calls(events)
    assert [c.name for c in calls] == ["shell", "mcp__cognitive__assess", "shell"]
    assert calls[0].is_error is None  # exit 0 → no failure signal
    assert calls[1].server == "cognitive"
    assert calls[2].is_error is True  # non-zero exit


def test_extract_tool_calls_drops_tools_from_aborted_attempt():
    # Tools before the last error belong to the aborted attempt; only post-error
    # tools (the successful retry) count — same rule as _extract_text.
    events = [
        {"type": "item.completed", "item": {"type": "command_execution", "command": "aborted", "exit_code": 0}},
        {"type": "turn.failed"},
        {"type": "item.completed", "item": {"type": "mcp_tool_call", "server": "s", "tool": "ok"}},
    ]
    calls = CodexBackend._extract_tool_calls(events)
    assert [c.name for c in calls] == ["mcp__s__ok"]


def test_extract_tool_calls_empty_when_no_tools():
    assert CodexBackend._extract_tool_calls([{"type": "turn.completed", "usage": {}}]) == []


# --- session resume (the vertical capability the base threads) --------------


def _argv(session_id=None):
    return CodexBackend()._build_argv(
        system_prompt="sys",
        user_message="hola",
        mcp_servers=[],
        tool_policy=ToolPolicy(),
        model=None,
        session_id=session_id,
    )


def test_build_argv_resumes_when_session_id_given():
    argv = _argv(session_id="thread_abc")
    assert argv[:3] == ["codex", "exec", "resume"]
    # resume REJECTS --sandbox (inherits the thread's policy) — verified vs the CLI
    assert "--sandbox" not in argv
    # id + prompt are the trailing positionals, options before them
    assert argv[-2:] == ["thread_abc", "sys\n\n---\n\nhola"]


def test_build_argv_no_resume_without_session_id():
    argv = _argv(session_id=None)
    assert "resume" not in argv
    assert argv[:3] == ["codex", "exec", "--json"]
    assert "--sandbox" in argv  # a fresh turn sets the sandbox


# --- output schema (JSONL) is Codex's, not the base's -----------------------


def test_json_lines_skips_blank_and_invalid():
    text = '{"a": 1}\n\n   \nnot json\n{"b": 2}\n'
    assert CodexBackend._json_lines(text) == [{"a": 1}, {"b": 2}]


def test_parse_output_builds_turn_result_from_stdout():
    stdout = (
        '{"type": "thread.started", "thread_id": "t9"}\n'
        '{"type": "item.completed", "item": {"type": "agent_message", "text": "hola"}}\n'
        '{"type": "item.completed", "item": {"type": "mcp_tool_call", "server": "s", "tool": "go"}}\n'
        '{"type": "turn.completed", "usage": {"output_tokens": 3}}\n'
    )
    result = CodexBackend()._parse_output(stdout)
    assert result.text == "hola"
    assert result.session_id == "t9"
    assert result.usage == {"output_tokens": 3}
    assert [t.name for t in result.tool_calls] == ["mcp__s__go"]


# --- integration: resume argv against the REAL codex (grammar smoke test) ----


@pytest.mark.integration
@pytest.mark.skipif(shutil.which("codex") is None, reason="needs the codex CLI on PATH")
def test_resume_argv_parses_against_real_codex():
    """Grammar-only smoke test (no auth, no turn): the resume argv must get PAST
    the real codex arg-parser. A bogus id fails with 'no rollout found' (a local
    lookup), NEVER 'unexpected argument' — which is exactly what `--sandbox` on
    resume used to produce. Guards against a flag drift between codex versions.
    Full end-to-end continuity is NOT covered here (it needs a logged-in codex and
    persistent ~/.codex storage — see _build_argv's caveat)."""
    argv = CodexBackend()._build_argv(
        system_prompt="",
        user_message="hi",
        mcp_servers=[],
        tool_policy=ToolPolicy(),
        model=None,
        session_id="00000000-0000-0000-0000-000000000000",
    )
    proc = subprocess.run(argv, capture_output=True, text=True, timeout=60)
    combined = proc.stdout + proc.stderr
    assert "unexpected argument" not in combined, combined  # every flag is valid for `resume`
