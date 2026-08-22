# FI-RUNNER-TOOLPOLICY-1 — safe non-coding "companion" tool profile (allowlist by default)

Status: **Done** — `ToolPolicy.companion()` vive en fi-runner y og118 lo usa (verificado 2026-08-22)
Proposed: 2026-06-21 by Bernard (via coagent adversarial review of the og118 filesystem-exposure fix)

## What it is

A framework-level tool posture in fi-runner so a `ClaudeCodeBackend` consumer that
is a **thinking companion** (not a coding agent) does NOT inherit Claude Code's
full filesystem/coding toolkit by default. Today, `permission_mode=BYPASS` grants
EVERY built-in except those explicitly denied — a fail-open denylist. og118
demonstrated the failure live: asked "show me your code", it ran `Glob` + `Read`
on its own container source (PR #277 closed it with a denylist hotfix).

The coagent's adversarial point: **the persona is not a security boundary; the
ToolPolicy is — and a denylist is the wrong model.** An allowlist (permit only the
explicit RAG/conversation tools, deny every filesystem/coding built-in by default)
is fail-safe: a new Claude Code built-in tomorrow is blocked by default instead of
silently slipping through a denylist.

## The capability to add (a new configurable level, per framework-canary-consumer)

A "companion" profile (opt-in) where:
- the backend does NOT assume coding-agent — filesystem/exec built-ins
  (Read/Grep/Glob/LS/Task/Bash/Write/Edit/NotebookEdit/…) are denied by default;
- only explicitly-allowed tools (the consumer's MCP capabilities — rag_store,
  task_tracker — plus any opt-ins) can run;
- it must work HEADLESSLY without hanging: a denied built-in is refused cleanly,
  NOT left to a permission prompt that blocks the turn (the reason BYPASS was
  chosen in the first place — so this is the real design problem to solve).
- A "coding" profile keeps filesystem access for consumers that genuinely need it.

Consumers that opt into companion: **og118, alice, ferboli, activist-os** — any
non-coding companion on `ClaudeCodeBackend`.

## Canonical path to reuse (Art. 6)

The mechanism already half-exists: `ToolPolicy.builtin_allowed` + `_allowlist()` in
`apps/packages/fi-runner/fi_runner/backends/claude_code.py`. The gap is making an
allowlist EFFECTIVE under headless operation (today `BYPASS` ignores it; non-bypass
modes prompt and hang). Solve that, expose it as a named profile, migrate og118
from the #277 denylist to the profile.

## Acceptance criteria (from the review)

- `Read`/`Grep`/`Glob`/`LS`/`Task`/`Bash`/`Write`/`Edit`/`NotebookEdit` are denied
  for a companion consumer EVEN IF the prompt explicitly asks for them;
- the RAG MCP tools (list/search documents) still run with no prompt, no hang;
- a new/unknown built-in is denied by default (allowlist, not denylist);
- og118 deleted its local denylist and consumes the companion profile (the
  wrapper ends up thinner — framework-canary-consumer).

## Status / next step

Not built yet. Deliberately AFTER the two leak hotfixes land+deploy (#277 then
#276) and the RAG lock/perms fix (#266). PR #277 is the consumer-level hotfix that
holds the line until this lands. Lesson: **BYPASS + ClaudeCodeBackend + thinking
companion is insecure by default.**

Related: PR #277 (the hotfix this supersedes), [[og118-identity-scoping-leak]].

## Cierre verificado (2026-08-22)

- El perfil es real: `apps/packages/fi-runner/fi_runner/backend.py:156`
  `COMPANION_BLOCKED_BUILTINS` (Bash, Write, Edit, NotebookEdit, Read, Grep,
  Glob, LS, Task + las 6 `Task*` del harness — éstas por una segunda razón:
  le hacen sombra al MCP `task_tracker` y rompen el stream glass-box del plan),
  y `:175` `ToolPolicy.companion(*, builtin_allowed=None, permission_mode=BYPASS)`.
- og118 lo consume en `server/runner.py:365` y **borró** su denylist local de #277.
- Tests: `fi-runner/tests/test_backend.py:41`.

**El criterio que quedó en el consumer, no en el framework.** Se pedía
*allowlist* (lo desconocido se niega por default); fi-runner sigue siendo
*denylist* bajo BYPASS. La allowlist real la puso og118 en
`server/runner.py:236` (`BackendAcotado`), que fija
`options.tools = ("WebSearch","WebFetch")` y lo **asegura** en `:135`
(`_verificar_superficie_acotada` truena si `tools` viene `None` o si se coló un
builtin bloqueado). Su propio docstring nombra el hueco: *"fi_runner nunca setea
`ClaudeAgentOptions.tools`, así que cualquier consumidor suyo hereda el preset
completo por default."*

**Residual (merece su propia tarjeta):** subir la disponibilidad de `tools=` a
`ToolPolicy` (un `builtin_available`) dentro de `ClaudeCodeBackend.build_options`,
para poder **borrar** `BackendAcotado` y que los demás companions hereden la
postura fail-safe en vez de la denylist. Hoy el único consumidor de
`companion()` fuera de tests es og118 (y fenix, que monta su runtime).
