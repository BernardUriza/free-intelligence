# fi-runner

A **backend-agnostic agent runner framework** over [fi-core](../fi-core).

The third tier of the Free Intelligence stack:

```
fi-core      primitives (cognitive, persona, rag, memory) — Python API + MCP servers
   ▼
fi-runner    THE FRAMEWORK — abstracts the agent HARNESS
   │   AgentBackend (port) ─► ClaudeCodeBackend (claude_agent_sdk · Max sub · MCP)
   │                          CodexBackend       (codex exec / SDK · v2)
   │                          [api]              (raw API via Pydantic AI · optional)
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
**Claude Code (Max subscription)** or **Codex (ChatGPT)** by swapping the backend.

The unifier: both harnesses are **MCP clients**, so fi-core capabilities
(`cognitive`, `persona`) plug into either via their MCP servers. fi-runner just
maps `capabilities=["cognitive"]` → `python -m fi_core.cognitive.mcp_server`.

## Install

```bash
pip install 'fi-runner[claude]'   # Claude Code backend
pip install 'fi-runner[codex]'    # Codex backend (v2)
```

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

Status: **alpha** — `ClaudeCodeBackend` works; `CodexBackend` is a v2 skeleton.
