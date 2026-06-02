# fi-runner — multi-platform SSOT contract

**Goal:** ship fi-runner to two ecosystems — **conda** (Python, the curated
scientific channel) and **npm** (TypeScript, so JS/Node apps run it sidecar-free)
— without maintaining two divergent codebases.

**Principle:** the single source of truth is **the contract, not the source
code.** Python and TS keep separate, idiomatic implementations; both conform to
one versioned contract. They are thin because the heavy dependency — the agent
CLI (`codex` / `claude`) — is **already a Node binary**, so a TS runner is
"Node calling Node," no transpiler, no WASM, no `subprocess`-over-Pyodide trap.

> ❌ Do **not** auto-convert Python→JS (Transcrypt / Pyodide). Pyodide can't
> `subprocess.spawn` — fatal, since spawning the CLI is the whole job.

---

## 1. The CLI contract (authoritative — Python side already implemented)

The shell-out surface every consumer uses (`fi_runner/cli.py`, Typer; the TS
package mirrors these command names, flags, and I/O **exactly**).

```
fi-runner exec PROMPT [options]      # one agent turn → stdout
fi-runner version                    # prints the version
```

`exec` options (stable contract):

| Flag | Default | Meaning |
|---|---|---|
| `PROMPT` (arg) | — | prompt text, or `-` to read stdin |
| `--backend, -b` | `codex` | `codex` \| `claude` |
| `--model, -m` | backend default | model / Azure deployment (e.g. `gpt-4.1`) |
| `--persona` | neutral default | system persona text |
| `--persona-file` | — | read persona from file (wins over `--persona`) |
| `--capability, -c` | — | fi-core capability MCP server (repeatable) |
| `--azure-endpoint` | `$FI_RUNNER_AZURE_ENDPOINT` | Azure OpenAI v1 endpoint (codex API-motor) |
| `--azure-key-env` | `AZURE_OPENAI_KEY` | env var holding the Azure key (never inline) |
| `--session-id, -s` | — | stateful conversation continuity |
| `--json` | off | emit `{text, session_id, tool_calls}` instead of plain text |

**I/O invariants** (both languages MUST match):
- Plain mode: result text → stdout, nothing else.
- `--json`: a single JSON object `{ "text": string, "session_id": string|null,
  "tool_calls": string[] }` → stdout.
- Errors → stderr, prefixed `error:`. Exit codes: `0` ok, `1` runtime failure,
  `2` bad input (empty prompt).
- Secrets are read from the environment, never passed inline.

A Java/Spring (or any) consumer runs `fi-runner exec "..." --json` via
`Runtime.exec` and parses stdout. No persistent service.

## 2. The type schemas to extract as JSON Schema (codegen → Python + TS)

These are the cross-language invariants. Define once in `contract/*.schema.json`;
generate Python `TypedDict`/dataclasses and TS `interface`s from them.

1. **Backend port** — what an `AgentBackend` accepts/returns: `run_turn(system_prompt,
   user_message, mcp_servers, tool_policy, model?, session_id?) -> TurnResult`.
   `TurnResult = { text, session_id?, tool_calls[], ... }`.
2. **Runner config** — `persona` (required, non-empty), `capabilities[]`,
   `tool_policy { permission_mode, builtin_allowed?, builtin_disallowed? }`,
   `extra_mcp_servers[]`, `retry_policy { max_attempts }`.
3. **Plan events** — the streamed plan-first event schema (the v2 task_tracker
   contract: declare/start/complete/fail/cancel step, note, insert, replan,
   cancel/finalize plan). Already the spine of `_plan_events.py` / `flow.py`.
4. **Agent-CLI JSON protocol** — the `codex exec --json` (and `claude`) line
   protocol fi-runner parses. Both runtimes spawn the same binary and parse the
   same frames, so this schema is shared verbatim.

## 3. Distribution map

| Platform | Package | Channel | Consumers |
|---|---|---|---|
| Python | `fi-runner` (this pkg) | **conda** (`bernardurizaorozco`, conda-forge in review) | fi-core stack, Insult AI, aurity |
| TypeScript | `fi-runner` (new pkg, mirror) | **npm** | Next.js / Node apps, sidecar-free |

Both expose the **same `fi-runner` CLI** (§1). conda stays the curated Python
channel (it manages the Node agent CLI as an env dep — pip cannot); npm opens the
JS ecosystem. **PyPI is intentionally skipped** — see
`memory/fi_runner_distribution_doctrine.md`.

## 4. CLI authoring doctrine (reused from `free-intelligence/backend`)

Both CLIs follow the `fi-coder` pattern: typed options, example-rich help, stdin
`-` piping, exit-code propagation, and a self-documenting `make`-style facade.
Python = **Typer**; TS = its npm analogue (commander / oclif).

---

## Build order

1. ✅ Python CLI (`fi_runner/cli.py`, Typer) + `[project.scripts]` + `[cli]` extra — **done, verified**.
2. ☐ Extract `contract/*.schema.json` (the four schemas above) from the current Python types.
3. ☐ Codegen Python types from the schemas (replace hand-written where they drift).
4. ☐ New TS package: mirror `Runner` + `CodexBackend` (spawn `codex exec --json` via `child_process`) + the same CLI.
5. ☐ Publish: conda (Python, existing flow) + npm (TS). Portfolio dogfoods via `fi-runner exec` shell-out.
