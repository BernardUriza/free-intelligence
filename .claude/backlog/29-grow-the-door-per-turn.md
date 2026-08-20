# Grow the door — per-turn model / tools / images for the fi-runner AIREBackend

Status: **In progress** — the tools MECHANISM + gap #1 (per-turn tools) shipped 2026-07-29
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

**The mechanism + gap #1 (per-turn tools) SHIPPED 2026-07-29.** Bernard chose the
"in-process registry AIRE ships" shape (never arbitrary specs — that would be RCE
on the root droplet). What landed:

- `engine/tools.py` — the registry: a turn selects vetted servers BY NAME
  (`{"tools":["memory"]}`); a dict/spec/unknown name is refused (the RCE vector is
  closed, unit-verified).
- `engine/memory_tool.py` — the first tenant: an in-process `memory` server with a
  `recall` tool over AIRE's OWN `claude_session_store`, session-scoped to the
  casita's project_key (a new sanctioned read, [[write-only-daemon]] §3).
- Wired through `messages.py` → `core.py` → `options.py`; tools require `mode=agent`
  (a 422 otherwise); tools are fixed at the session's first turn (like mode).
- **Verified E2E** against a local daemon on the real Postgres: the agent called
  `mcp__memory__recall` through the door (mode=agent, $0.21), and `recall` retrieves
  real transcript rows (tested directly against a prod project_key). Thirty-line law
  green.

**Gap #3 (model) SHIPPED 2026-08-20** (`a40f389`) — the door takes `model` in the
body; the turn's shape (mode, tools, model) now travels as one frozen `TurnSpec`
through edge → engine → options → the CLI's `--model`. All three bind when the
session's pooled client is (re)born (the SDK takes them at construction). The
result's `model` is PROVENANCE, not an echo: drained off the `AssistantMessage`s,
so it names the model that actually answered — verified from outside the droplet:
asking `"haiku"` answered with `"model": "claude-haiku-4-5-20251001"` ($0.028),
no model answered `"claude-sonnet-5"` (the engine-decided default, previously
blind), and a garbage name got the 422. The edge guards only the argv's shape;
the API curates the catalog.

Remaining gaps (this item stays open until they close or Bernard scopes them out):
- **Gap #2/#4** — per-turn `system_prompt` / `images` (unbuilt).
- **The consumer side**: fi-runner's `AIREBackend` still REJECTS `mcp_servers` —
  next it must translate a consumer's tool needs into registry tool NAMES and pass
  `tools=[…]` to the door. That unblocks discord-bot's real turn on AIRE. Its
  `model` reject clause can now become a forward clause too (`_warn_unenforceable`
  → pass `model` in the body, read the result's provenance) — fi-runner repo work.
- **More registry tenants**: `memory/recall` is AIRE-agnostic (its own transcript).
  Consumer-specific servers (og118's rag_store, discord-bot's persona_memory) are a
  further identity fork — does AIRE host consumer schemas? — deferred to Bernard.

See fi-runner backlog `fi-runner-aire-backend.md` and [[ssh-is-a-missing-endpoint]].
