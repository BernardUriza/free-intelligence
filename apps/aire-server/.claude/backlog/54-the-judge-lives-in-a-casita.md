# 54 — The Stop judge lives in a casita: one fixed casita, a persona, memory, and it learns every turn

Status: **In progress**
Proposed: 2026-11-12 by Bernard (*"la intencion de pasar el juez por AIRE es que se usara una casita que
escriba memorias y sea mas listo cada vez y se llame la misma casita siempre, o sea, usar lo que hicimos de
free-intelligence realmente, ahorita no se usa, es solo decoracion, la persona, la memoria el mcp, todo esta
muerto"*).

## What it is

Today the four Stop judges (`personal-stop-judge`, `thinkpad-stop-judge`, `visalaw-judge`, and the shape
`susurro-diarize` shares) call the stateless `/openai/v1` door (#51): one `chat/completions` to Azure
`gpt-5.4-mini` per verdict, no casita, no session, no memory. `aire_gateway_log` holds 643 judge rows since
2026-10-28 with `project` and `session_id` empty on every one. The judge forgets each verdict the moment it
gives it, so it can never learn from a block it got wrong. Every FI piece built for exactly this — the casita
persona (#36), the `memory` tool (#29), MCP tools (#48) — goes unused by it.

The target: every judge verdict is a turn on the message door,
`POST /projects/stop-judge/sessions/<s>/messages`, in ONE fixed casita whose persona is the rubric, and the
casita writes down what it learns (a false positive Bernard overrode, a pattern that keeps failing) so that
the next verdict reads it.

## Measured 2026-11-12 (before this card)

- Codex through the door works and keeps the thread: casita `stop-judge`, session `probe-1112`,
  `provider: "codex"`, `mode: "complete"` → `PASS` in **10.4 s** cold; the second turn answered
  *"Me pediste que respondiera solo: PASS."* in **8.8 s**. The `/openai/v1` judge takes ~3 s
  (`stop-judge-aire/log.jsonl`, `seconds`).
- **The Codex backend has no MCP**: `agent_sdk/codex.py` passes no `mcp_servers`, and `engine/tools.py`
  builds the `memory` server only for the SDK path. A Codex judge cannot call `recall` today.
- `recall` is an `ILIKE` over `claude_session_store.entry` (`engine/memory_tool.py`); Codex turns are mirrored
  by `acp_mirror`, so whether `recall` would even see a Codex casita's rows is unverified.

## Canonical path to reuse (Art. 6)

The casita persona (`init_project`, `codex_persona.py` → `AGENTS.md`), the `memory` tool, remote tools (#48),
the credential rotor (#53: Codex plan seat first, `metered=f`). The judge adapter is
`agent-constitution/gates/stop-judge/gate.py`; its http transport is the seam that changes doors.

## The decisions that are Bernard's

1. Provider: Codex (plan seat, no MCP yet → #54 includes giving the Codex backend MCP) or Claude (the SDK
   path already has `memory` + MCP, but it draws on the Max pool).
2. Session shape: one session forever (context grows without bound) or a session per day/repo with the
   learning carried in casita memory files.
3. Latency budget: a Stop that waits ~9–10 s on every reply, or verdict stays on the fast door and the
   casita learns asynchronously from the log.

## Decided 2026-11-12 (Bernard)

1. **Codex, and the Codex backend gets MCP** — so every Codex casita gains `memory`, not just the judge.
2. **One casita `stop-judge`, a session per day**; what it learns lives in the casita's memory and persona.
3. **Every verdict goes through the casita** (~9–10 s per Stop accepted); one path, no fast-door shadow.

## Status / next step

In progress. First PR (Codex gets `memory`): a turn with `provider: "codex"` and `tools: ["memory"]` declares a
stdio MCP server per turn through `codex exec -c mcp_servers.memory.*` (`agent_sdk/codex_mcp.py`); its child is
`python -m aire.engine.stdio_tool memory <project_key> <cwd>`, which serves the SAME server object the SDK mounts
in-process. `recall` now reads `claude_session_store` AND `aire_agent_log`, so a Codex casita finds its own
rows (the open question above: it did not, Codex rows never reach the SDK store). Shaped by codex-cli 0.164.0's
source: the child's env is scrubbed (the DSN rides as `env_vars`, a name, never a value in argv) and under
`approval_policy="never"` an MCP call that needs approval is denied, so the server is `approve`. Only `memory`
is offered to Codex; any other registry name logs `CODEX-TOOL-UNSUPPORTED`. Proven locally against a fake
model that spawns the real server the way codex does. NOT yet proven on the droplet with the real CLI.

Next: deploy, then one real Codex turn through the door with `tools: ["memory"]` that recalls an earlier
session's word; then the judge adapter's transport points at the message door.

## 2026-11-12 23:45Z — memory works live on the droplet (#639–#642)

The first live run failed: the model said *"No tengo acceso a recall"* and listed 195 `mcp__codex_apps__*`
tools and none from `memory`. `RUST_LOG=trace` on the droplet showed the server initialize and answer
`tools/list`, then `omitting pending optional MCP server server_name=memory`
(`codex-mcp/src/connection_manager/tool_catalog.rs:376` at `rust-v0.164.0`): an optional server past the
startup grace is dropped from the turn's catalog. `mcp_servers.memory.required=true` (#642) makes codex wait.
Receipt: session `mem-g-1112` was told `guanabana-20314`; a NEW session `mem-h-1112` with `tools: ["memory"]`
answered `guanabana-20314` in 18.5 s, and `aire_agent_log` holds the `mcp_tool_call` `memory/recall`
`status: completed`. Side fixes: `recall` survives a box without `claude_session_store`; a clean Codex turn
keeps its stderr (`kind=stderr`); MCP turns run with `RUST_LOG` for the server's logs.

Cost note: every Codex turn carries the plan's ~195 `codex_apps` tools (~24K cached input tokens).

Next: the judge adapter (`agent-constitution/gates/stop-judge`) moves its transport to the message door,
casita `stop-judge`, session per day, `tools: ["memory"]`.
