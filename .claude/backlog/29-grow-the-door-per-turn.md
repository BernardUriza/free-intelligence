# Grow the door — per-turn model / tools / images for the fi-runner AIREBackend

Status: **Proposed** 2026-07-27 by Claude (surfaced building fi-runner's AIREBackend)
Proposed: 2026-07-27

## What it is

fi-runner now has an `AIREBackend` — a third `AgentBackend` (peer to
`ClaudeCodeBackend` / `CodexBackend`) that is an HTTP client of this door
(`apps/packages/fi-runner/fi_runner/backends/aire.py`, first cut verified E2E
against `gate.bernarduriza.com` on 2026-07-27). It faithfully covers the
**companion / text turn**: `mode=complete`, memory owned by AIRE.

But `AgentBackend.run_turn` carries four per-turn inputs the door does NOT accept
today — the message endpoint takes only `{message, mode, background}`. So the
backend REJECTS them loudly rather than answer wrong. Each rejection is a door
gap to close, and this is the [[ssh-is-a-missing-endpoint]] formula applied to
the socket: *a capability fi reaches for that the door lacks → a new door param.*

The four gaps, in the order fi will need them:

1. **`mcp_servers` (per-turn tools).** ClaudeCodeBackend passes the runner's MCP
   servers + allowlist per turn; the door configures tools server-side (`MODES`
   in `engine/options.py`), so a tool turn on AIREBackend raises. This is the big
   one: it unblocks og118's rag_store / task_tracker companions on AIRE. Needs the
   door to accept an mcp/tool spec per turn AND the engine to mount it (bounded by
   the casita cage, #24).
2. **`system_prompt` per turn.** Today it rides via `/init` as the casita's fixed
   `CLAUDE.md` (per-project, re-sent only on change). Fine for a stable persona;
   a caller that varies the system prompt per turn has no path. Decide whether
   that is even wanted (the init model is arguably better — content, not repeated
   per message) or a real gap.
3. **`model` per turn.** The runner's `ModelRouter` picks a model; the door
   ignores it and the engine decides. The result's `model` is left `None` (honest
   "engine-decided") rather than echoing an unhonoured request — so provenance is
   blind until the door accepts + reports the model.
4. **`images` (vision).** No per-turn image blocks; a vision turn raises. Needs
   the door to accept base64 image blocks and the engine to fold them into the
   SDK's streaming-input mode (ClaudeCodeBackend already does this locally).

## Canonical path to reuse (Art. 6)

- The fi-runner side already speaks the exact contract: `AIREBackend` reconstructs
  fi's `TurnResult` / `ToolCall` / stream events from the door's SSE. Growing the
  door means the *engine* honours more of what fi already sends — the backend's
  reject-clauses become forward-clauses, one gap at a time.
- The event vocabulary is already shared (`text` / `tool_call` / `result`), copied
  from fi's contract into `engine/contract.py`. Adding tools does NOT change the
  event shape — only what the engine runs.

## The decision that's the owner's

- **Order and scope.** #1 (tools) is what makes AIREBackend a real replacement for
  ClaudeCodeBackend in og118; the rest are narrower. Bernard picks whether to
  close all four or stop at the companion turn.
- **The tools-vs-cage tension.** Per-turn MCP tools on the droplet must stay inside
  the casita cage (#24) and the spend caps (#23/#25) — growing the door widens the
  attack surface the cage just closed. His call on how far.

## Status / next step

Not built. The first-cut backend ships with each gap rejected loudly + documented,
so nothing lies. Next when Bernard greenlights: start with #1 (per-turn tools),
because it is the one that unblocks a real consumer. See fi-runner backlog
`fi-runner-aire-backend.md` (the consumer side) and
[[ssh-is-a-missing-endpoint]].
