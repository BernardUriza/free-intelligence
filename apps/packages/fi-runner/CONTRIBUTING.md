# Contributing to fi-runner

fi-runner is a backend-agnostic agent runtime: it wraps ONE agent harness (Claude Code, Codex, raw API) at a time and runs a single turn given a system prompt, a user message, MCP servers, and a `ToolPolicy`.

Consumers depend on `fi-runner` rather than wiring their own runtime per project. Swap the backend, keep the runner.

---

## Dev setup

```bash
# From the repo root (BernardUriza/free-intelligence):
cd apps/packages/fi-runner
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest                      # 193+ tests should pass
```

`fi-runner` depends on `fi-core>=0.24,<0.25`. The dev install pulls it from PyPI; for editable local fi-core dev:

```bash
pip install -e ../fi-core
```

---

## Where the code lives

```
fi_runner/
├── __init__.py            # public API (__all__ = 56+ exports)
├── backend.py             # AgentBackend Protocol + ToolPolicy + MCPServerSpec
├── backends/              # concrete backends (Claude Code, Codex)
├── runner.py              # Runner — the turn pipeline orchestrator
├── capabilities.py        # fi-core capability factories (cognitive, persona, …)
├── guards.py              # deterministic in-process safety nets
├── plan_guard.py          # plan-first anti-drift
├── conversation.py        # ConversationStore + history-replay continuity
├── pipeline.py            # post-processor pipeline + run_pipeline
├── flow.py                # turn-flow Mermaid renderer
├── narrate.py             # FlowNarrator background refinement
├── _flow_delivery.py      # internal: mechanical + narrated diagram delivery
├── _guards_executor.py    # internal: guard list execution
├── _plan_events.py        # internal: plan-first stream-event derivation
├── _runner_config.py      # RetryPolicy + FlowNarrator dataclasses
├── preflight.py           # MCP server probe
├── packs.py               # re-exports of fi_core.persona built-in pattern packs
├── router.py              # ModelRouter for per-turn model selection
└── rag_store.py           # rag_store capability
```

---

## When NOT to change fi-runner

fi-runner stays backend-agnostic. Before adding code:

- **A specific backend's quirk** (e.g., a Claude SDK option, a Codex flag) → goes in `backends/<that-backend>.py`, not in `runner.py`.
- **A specific consumer's pipeline logic** → goes in the consumer's repo, not in fi-runner.
- **fi-core primitives** (RAG chunking, embedders, persona detection, training pipes, memory) → that's `fi-core`. fi-runner DEPENDS on fi-core; it doesn't copy fi-core code in.

If your change feels like it's growing fi-runner toward a specific consumer, stop and propose a fi-core API change OR a guard / capability factory instead.

---

## Guards vs capabilities

This is the framework's central distinction:

| | Guards | Capabilities |
|---|--------|--------------|
| Where | in-process, runs every turn | optional MCP tools the LLM *may* call |
| Determinism | deterministic, guaranteed | LLM-discretionary |
| Use for | safety nets (triage escalation, anti-drift) | structured data exchange (cognitive flow, RAG search) |

If you find yourself wanting "this MUST happen every turn", it's a GUARD. If "the agent CAN use this when relevant", it's a CAPABILITY.

---

## PR conventions

- **Conventional Commits**: `feat:`, `fix:`, `refactor:`, `chore:`, `docs:`, `test:`.
- **One concern per PR**: never mix packaging + logic; never bundle multiple unrelated feature additions.
- **Tests required** for new public surface. Run `pytest` before pushing.
- **Type-clean**: `mypy` / `pyright` should pass; `py.typed` marker means downstream consumers rely on the annotations.
- **English** in docs and comments.

---

## Release process

See [`RELEASE.md`](RELEASE.md). Releases are tag-driven (`fi-runner-vX.Y.Z`). The Golden Rule: before cutting a tag, run the external-user smoke test from a CLEAN conda env, follow the README literally. If anything fails, fix it BEFORE releasing.

---

## License

MIT.
