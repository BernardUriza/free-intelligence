# The living casita prompt — the agent rewrites its own CLAUDE.md, per chat

Status: **Done 2026-08-21, both halves** — AIRE (`df0acae` + `5ae8e33`) and
og118 (fi PR #411, merged + deployed). Measured on the LIVE product: a fresh
chat in app.og118.ai got its own casita (`og118-03afad73-…`), og118 wrote its
own living part ("Usuario: Bernard / Tema: astronomía / una sola frase") via
`mcp__persona__update` in `mode=complete`, and the NEXT turn obeyed it —
a white-dwarf question answered in exactly one sentence. Same-day refinement,
Bernard's catch: chats were born FAT (a full base copy each — N frozen copies).
Now a chat file is born THIN — `@base og118` + soul — and the engine
dereferences the shared base at spawn (`ef21e68`; og118 side fi PR #413).
Verified live: a fresh jazz chat's whole CLAUDE.md is the stub line, the
marker, and two sentences of soul, and the reply closed with the dato curioso
its soul asks for
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

Greenlit by Bernard the same day (casita per chat, protected base) and the AIRE
half SHIPPED, measured live on 2026-08-21 against casita `personatest36`:

1. **The tool works in `mode=complete`** — the old 422 guard fell (`5ae8e33`):
   a real haiku turn with `tools:["persona"]` executed `mcp__persona__update`
   in 462ms, no hang, $0.033. The mode dial governs builtins only.
2. **The base is protected** — after the agent's update, the file read back as
   base + marker + *"I have learned the user is Bernard and he likes
   receipts."*; a re-init with a new base refreshed the base and the living
   part SURVIVED (rebase in `init_project.py`).
3. **The magic is real** — a brand-new session (`living-2`, no tools) answered
   *"The user is Bernard, and he likes receipts."*: the identity an agent
   writes takes effect from the very next spawn.

The og118 half landed the same day (fi PR #411): casita-per-chat naming
(`og118-{conversationId}`), per-chat init with the base + a LIVING IDENTITY
paragraph (prompts-as-content), `tools:["persona"]` riding `mode=complete`
after the guard fell, and the latent FlowNarrator hazard closed. Verified on
the live tutor end-to-end.
