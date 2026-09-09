# FI-RUNNER-TOOLPOLICY-1 — safe non-coding "companion" tool profile (allowlist by default)

Status: **Done, y su residual quedó SIN OBJETO** (re-verificado 2026-09-09) — `ToolPolicy.companion()` sigue vivo en fi-runner pero **ya no tiene consumidores**: la consolidación a AIRE borró el backend que lo honraba. Lo que acota los tools hoy es el dial de modos de AIRE, server-side. Ver la última sección; las de 2026-08-22 son históricas
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

## Cierre verificado (2026-08-22) — HISTÓRICO, superado por la sección final

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

## El residual quedó SIN OBJETO — y lo que destapó (2026-09-09)

El residual pedía subir `tools=` a `ToolPolicy` dentro de
`ClaudeCodeBackend.build_options` para poder borrar `BackendAcotado`. **Las dos
piezas que nombra están muertas**, ambas en el commit `23019587` (2026-08-29, la
consolidación a AIRE): `ClaudeCodeBackend` se borró junto con `CodexBackend` y
`SubprocessCLIBackend` (`fi_runner/backends/__init__.py` lo documenta), y con él
se fue `BackendAcotado` de og118 — hoy sólo sobrevive como prosa en el nombre de
`server/tests/test_capability_surface_is_bounded.py`. No hay dónde poner un
`builtin_available`: no queda backend que construya `ClaudeAgentOptions`.

**Lo que sí es cierto hoy, verificado:**

- `ToolPolicy.companion()` **no tiene un solo consumidor vivo** — sólo
  `tests/test_backend.py`. og118 manda `ToolPolicy()` pelado
  (`server/runner.py:328`) y explica por qué en el mismo sitio.
- `AIREBackend` **no reenvía `tool_policy`** (`backends/aire.py:45`). Quien acota
  de verdad es el dial de modos de AIRE, server-side: `complete` no concede
  ningún builtin, `agent` concede `Read/Write/Glob/Grep/WebSearch/WebFetch`, y
  **`Bash` está prohibido en los dos** (`aire-server
  server/aire/engine/options.py:63-74`), más la jaula `PreToolUse` que niega todo
  tool de archivo fuera de la casita (`aire-server server/aire/engine/cage.py`).
- **El hueco que esto destapó, ya cerrado:** `_warn_unenforceable` avisaba por
  `builtin_allowed` y por un `permission_mode` no-default, **pero no por
  `builtin_disallowed`** — o sea, la forma exacta que produce `companion()` con
  modo default cruzaba en SILENCIO. Corregido + 4 tests (`tests/test_aire_backend.py`).
- **Cuatro archivos de fenix afirmaban una garantía que nadie ejercía:**
  presupuesto.py, fenix_mcp.py, regularizacion.py y fenix_app.py decían
  *"`ToolPolicy.companion()` le bloquea `Bash`, `Write` y `Edit`"*. Falso dos
  veces: la llamada no ocurre, y el runner del tutor corre en `aire_mode="agent"`
  (`fenix_app.py:651`), donde **`Write` SÍ está concedido** (confinado a la
  casita). El diseño —el servidor genera el .xlsx, no el modelo— sigue siendo el
  correcto; la razón escrita era falsa y se corrigió a la real. Importa porque
  fenix tiene usuarios reales.

**Lo único que queda es de otro repo y es decisión de Bernard: aire-server #37**
(que la puerta acepte una postura de tools por turno). Hasta entonces, una
denylist de fi-runner es documentación, no un candado — y el warning es lo que
mantiene esa diferencia visible. Ver [[fi-runner-aire-backend]].
