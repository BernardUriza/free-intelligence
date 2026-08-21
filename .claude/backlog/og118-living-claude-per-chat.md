# OG118-LIVING-CLAUDE — a CLAUDE.md per chat, that the agent itself rewrites

Status: Proposed
Proposed: 2026-08-21 by Bernard (in the aire-server session, the moment the
front first rendered og118's casita CLAUDE.md — "ahí es donde se libera el
hueco de un feature que yo quería… el claude dentro debe ser distinto! debe ser
acorde al chat y debe de modificarse con las mcp tools de fi runner! magia")

## What it is

Today og118's casita on AIRE holds ONE fixed prompt (`CLAUDE.md`, installed by
`/init`) shared by every chat. Bernard's feature: **the CLAUDE.md must be
per-CHAT and ALIVE** — each conversation carries its own identity file, shaped
by that conversation, and the agent modifies it itself through MCP tools (the
fi-runner tool style: declared, glass-box, visible to the user). The persona
stops being a deploy artifact and becomes state the conversation grows.

## Why half of it already exists (discovered 2026-08-21, the day of the flip)

- og118 now speaks through AIRE's engine door (fi PR #409 + the prod flip).
  AIRE's cage confines file tools to the casita — which means **an agent-mode
  session can ALREADY `Write` its own casita's `CLAUDE.md`**, and the next
  spawn reads it. The self-editing-identity primitive is structurally free.
- The front already renders the casita's CLAUDE.md (folder + session views,
  via AIRE's artifacts door) — the "see the living identity" half is shipped.

## What is actually missing

1. **Per-chat scoping.** One casita = one prompt today. Either each chat maps
   to its own casita (AIRE already derives a casita per project NAME — a
   `og118-{chatId}` naming convention is zero new AIRE code), or the engine
   learns per-session prompt files. The first is the Art. 6 path.
2. **A safe edit tool in `mode=complete`.** og118 runs complete mode (no file
   tools). The agent needs a declared tool — `persona__read` / `persona__update`
   — surfaced through AIRE's tool registry (the memory-tool pattern,
   aire-server #29/#12), NOT a local MCP process (those don't exist on the
   droplet — measured during the migration, they 422).
3. **og118's UI** exposing that the identity changed (it already re-sends
   history; the persona chip could show "identity updated" events).

## Canonical path to reuse (Art. 6)

- AIRE's tool registry + `memory_tool.py` pattern (aire-server) for the
  persona tool — same session-scoped closure, casita-confined.
- The fi-runner declared-tool convention (task_tracker's declare/start/complete
  shape) for how the agent narrates the edit in the open.
- The front's `CasitaPrompt` panel already displays whatever the file becomes.

## The decision that's the owner's

- **Scoping:** casita-per-chat (memory fully splits per conversation) vs one
  casita with per-chat prompt files (shared memory, split identity). This
  changes what "og118 remembers" means — Bernard's call.
- Whether the base persona (Oganesson) is a protected preamble the agent can
  never delete, with the living part layered under it (recommended — an agent
  that can erase its own constraints erases its cage's manners).
- Whether identity edits are per-chat only or can promote to the shared base.

## Status / next step

Proposed. The AIRE-side slice is tracked in aire-server backlog #36; this item
owns the og118/fi-runner product half (tool wiring in `AIREBackend`, UI).
