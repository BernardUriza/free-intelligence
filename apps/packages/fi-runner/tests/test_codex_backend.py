"""Unit tests for CodexBackend's SDK-free helpers (no `codex` CLI required).

Everything CodexBackend decides before it ever spawns a subprocess lives in pure
helpers: which provider `-c` overrides to emit, which sandbox a ToolPolicy maps
to, and how to parse the JSONL event stream. Those are locked down here — most
importantly the API-motor provider config and the content-filter retry bug.
"""

from __future__ import annotations

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
