# 54 — The Stop judge lives in a casita: one fixed casita, a persona, memory, and it learns every turn

Status: **Accepted**
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

Accepted. First PR: MCP for the Codex backend (`memory` reachable from `codex exec`, project-scoped like the
SDK path). Then the judge adapter's transport points at the message door.
