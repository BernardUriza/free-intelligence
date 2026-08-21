# The living casita prompt — the agent rewrites its own CLAUDE.md, per chat

Status: Proposed
Proposed: 2026-08-21 by Bernard (the moment the front first rendered og118's
casita CLAUDE.md: *"el claude dentro debe ser distinto! debe ser acorde al
chat y debe de modificarse con las mcp tools de fi runner! magia"*)

## What it is

AIRE's slice of og118's living-identity feature (canonical product item:
`free-intelligence/.claude/backlog/og118-living-claude-per-chat.md`). The fixed
prompt a casita stands on stops being a deploy artifact: it becomes per-chat
state that the AGENT ITSELF edits through a declared tool, visible in the
front's `CasitaPrompt` panel (shipped 2026-08-21) the moment it changes.

## What AIRE already has (don't rebuild it)

- **The write primitive:** the cage scopes file tools to the casita, so an
  agent-mode session can already `Write` its own `CLAUDE.md`; the next spawn
  reads it. Verified structurally (cage.py, #24) — the magic is not new code.
- **Per-name casitas:** a project name IS a casita (`keys.py`); a per-chat
  identity can be per-chat project naming with zero engine changes.
- **The tool registry + memory tool** (#29): the pattern for a session-scoped,
  casita-confined tool served in `mode=complete` — the mode og118 runs, where
  file tools don't exist. The persona tool is its second tenant.
- **The showcase:** the front renders the casita's CLAUDE.md on the folder and
  every session page (artifacts door, `1b4c239`).

## The work, if Bernard greenlights

1. A `persona` tool pair in the registry (`read` / `update`), closing over the
   session's casita exactly as `memory_tool.py` closes over its project_key.
   Guardrail worth recommending: the base persona is a protected preamble the
   tool cannot delete — the living part layers beneath it.
2. Decide (with the og118 half) the scoping: casita-per-chat vs per-chat
   prompt files in one casita. The first is zero AIRE code; the second touches
   `engine/options.py`.
3. Nothing in the front: `CasitaPrompt` already shows whatever the file says.

## The decision that's the owner's

The scoping fork above (it decides what "og118 remembers" means), and whether
a self-edited identity may ever promote back into the shared base persona.

## Status / next step

Proposed — captured the day the hueco surfaced; not greenlit as build work yet.
