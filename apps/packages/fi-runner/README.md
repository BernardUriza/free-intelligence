# fi-runner

A **backend-agnostic agent runner framework** over [fi-core](../fi-core).

The third tier of the Free Intelligence stack:

```
fi-core      primitives (cognitive, persona, rag, memory) — Python API + MCP servers
   ▼
fi-runner    THE FRAMEWORK — abstracts the agent HARNESS
   │   AgentBackend (port) ─► ClaudeCodeBackend (claude_agent_sdk · Max sub · MCP)
   │                          CodexBackend       (codex exec --json)
   │                            ├─ ChatGPT login          → subscription mode
   │                            └─ ProviderConfig         → API motor (Azure/OpenAI/…)
   │   Runner: backend + persona + capabilities (fi-core MCP servers)
   │   ToolPolicy: per-runner security (built-in tools allow/deny, permission mode)
   ▼
runners      insult · alice · fi-medic   (config + composition; live in their own repos)
```

## Why a framework (not copy-paste)

`insult` runs on the Claude Agent SDK (Claude-only); `alice` on raw OpenAI chat.
Both re-implement the runner scaffolding. fi-runner extracts the **harness
abstraction**: a runner declares *what* it wants (a persona, fi-core
capabilities, a tool policy) and picks a backend — the same runner code runs on
**Claude Code (Max subscription)** or **Codex** by swapping the backend. And
Codex itself runs in two modes: a **ChatGPT login**, or — via a `ProviderConfig`
— as an **API motor** against any OpenAI-compatible endpoint (Azure, OpenAI,
OpenRouter, a local vLLM, …), no subscription, just the key in the environment.

The unifier: both harnesses are **MCP clients**, so fi-core capabilities
(`cognitive`, `persona`) plug into either via their MCP servers. fi-runner just
maps `capabilities=["cognitive"]` → `python -m fi_core.cognitive.mcp_server`.

## Install

```bash
pip install 'fi-runner[claude]'   # Claude Code backend (claude_agent_sdk)
pip install 'fi-runner[codex]'    # Codex backend (codex exec --json)
pip install 'fi-runner[cli]'      # the `fi-runner` shell-out CLI (Typer)
```

The conda package (`bernardurizaorozco` channel) ships the CLI by default.

## CLI — run a turn without importing Python

Any process (a shell, a Makefile, a CI step, or a non-Python backend via
`Runtime.exec`) can drive a Runner without a persistent sidecar — exactly how
fi-runner itself shells out to `codex exec --json`:

```bash
fi-runner exec "Summarize this repo" --backend codex --model gpt-4.1
echo "70yo male, chest pain" | fi-runner exec - --persona-file medic.md
fi-runner exec "What changed in this PR?" --json --session-id pr-42
```

Plain mode prints the text to stdout; `--json` emits
`{text, session_id, tool_calls}`. Secrets stay in the environment
(`--azure-endpoint` / `--azure-key-env`). This is the Python half of the
conda+npm SSOT — see [`docs/SSOT_CONTRACT.md`](docs/SSOT_CONTRACT.md).

## Usage

```python
import asyncio
from fi_runner import Runner, ClaudeCodeBackend, ToolPolicy, PermissionMode

medic = Runner(
    backend=ClaudeCodeBackend(default_model="claude-sonnet-4-5"),
    persona="You are a cardiology decision-support assistant. ...",
    capabilities=["cognitive"],                       # fi-core MCP server, auto-wired
    tool_policy=ToolPolicy(builtin_disallowed=["Bash", "Write", "Edit"]),  # PHI safety
)
print(asyncio.run(medic.run("70yo male, chest pain + dyspnea, HTN/DM")).text)
```

Same runner, no subscription — point Codex at any OpenAI-compatible API with a
`ProviderConfig` (the key is read from the environment, never passed inline):

```python
from fi_runner import Runner, CodexBackend, ProviderConfig

companion = Runner(
    backend=CodexBackend(
        default_model="gpt-4.1",
        provider=ProviderConfig(
            id="azure",
            base_url="https://<res>.openai.azure.com/openai/v1",
            env_key="AZURE_OPENAI_API_KEY",
            name="Azure OpenAI",
        ),
    ),
    persona="You are a warm, attentive companion. ...",
    capabilities=["cognitive"],
)
print(asyncio.run(companion.run("how are you?")).text)
```

Status: **alpha** — `ClaudeCodeBackend` (pooled sessions) and `CodexBackend`
(`codex exec --json`, subscription + API-motor modes) are in production.
