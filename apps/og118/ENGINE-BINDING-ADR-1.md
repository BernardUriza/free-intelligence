# ENGINE-BINDING-ADR-1 — how an elemento binds to an engine

Status: Accepted (Phase 1 shipped) — Phases 2–3 deferred
Decided: 2026-06-28 by Bernard (with the AURITY coagent's stress-test)
Supersedes nothing. Extends OG118-ELEMENTS-ADR-1.

## Context

An "elemento" swaps the answering persona. Today every active element runs on
og118's own backend (fi-runner + ClaudeCodeBackend) with a local persona `.md`.

Two problems surfaced when Oxígeno (Vultur Analytica) shipped:

1. **Persona duplication / drift.** The Vultur persona exists in TWO repos —
   `discord-bot/shared/personas/vultur.md` (the live Discord bot) and og118's
   `008-o-oxigeno.md` (an adapted copy). They had already diverged in their
   operative-context block. Editing the character in one does not reach the other.

2. **The "og118 is just a mask" idea.** Bernard's intent: og118 should be a
   surface; for some elements the *engine* (the thing that reasons) should live
   elsewhere — e.g. reuse the discord-bot's already-running Vultur — instead of
   og118 owning a copied persona and its own runtime.

## The decision

An element declares an **`engineBinding`** — NOT a vague "mode". `mode` collapses
distinct concerns (local persona, external HTTP, disabled, provider, routing). The
binding names exactly *how the element's turn is executed*:

| `engineBinding.kind`      | meaning                                                        |
|---------------------------|----------------------------------------------------------------|
| `local_runner_persona`    | og118's fi-runner runs the turn with a persona (today's path)  |
| `shared_persona_prompt`   | same engine, but the persona is a shared SSOT (not a copy)     |
| `external_http_engine`    | og118 proxies the turn to an external FI-contract engine       |
| *(future)* `mcp_agent`, `remote_runner` | reserved                                       |

### Layer ownership (where each piece lives)

- **og118** keeps the element registry: 118 slots, atomic number, symbol, cap,
  status, the Oxígeno→Vultur mapping, product copy. Chemistry stays in og118.
- **fi-core** holds the pure *types* only if/when shared: `EngineBinding`,
  `EngineBindingKind`, `PersonaRef`. No Oxygen/Oganesson/118/Vultur in core.
- **fi-runner** holds *execution*: resolve binding → call local or remote engine,
  normalize the response, translate external events → FI stream events,
  timeouts/retries, service auth, trace, streaming.
- **fi-glass** knows nothing about engines. It shows the active persona, the
  stream, the trace, the messages, the selector. The PersonaSelector does not care
  whether Oxígeno runs local or remote.

## Why NOT make the Discord bot the engine

A surface is not an engine. Making og118 call the discord-bot to reason is "like
making og118 call Slack to reason" (the coagent's stress-test). The discord-bot is
*another mask*; the shared thing is the **persona**, not the bot's runtime.
Proxying og118 → a live Discord gateway bot reopens exactly the guarantees og118
just earned:

- **P0 cross-user memory leak** — if Vultur has per-channel/server Discord memory,
  connecting it to og118 without designed tenancy mixes users' data. (og118 just
  shipped identity-scoped local-first stores to fix a same-device leak.)
- **P0 tool exposure** — an external engine with its own tools can reopen the
  filesystem/tool leak the COMPANION policy closed (#277/#291).
- **P1 lost trace** — if the engine only returns text, the glass-box stream
  (declare_plan/step/tool_call/result) — og118's differentiator — dies.
- **P1 lost continuity** — if it does not accept history-replay, og118 stops
  owning the thread (it is local-first by design).
- **P1 operational coupling** — if the Discord gateway/runtime falls, Oxígeno
  falls inside og118.

## Phased plan

### Phase 1 — PERSONA-SSOT-1 (SHIPPED 2026-06-28)

Kill the drift WITHOUT changing the runtime boundary, WITHOUT building an HTTP
engine, WITHOUT touching trace/history/voice/identity:

- The shared Vultur **core** lives once in `apps/packages/fi-personas/personas/vultur.core.md`,
  with a `<!-- CONTEXTO_OPERATIVO -->` splice marker.
- og118's Oxígeno composes `core` + its own `008-o-oxigeno.context.md` block (the
  registry gains `personaCorePath`; `composed_persona()` does the splice; the old
  standalone copy is deleted).
- `engineBinding.kind` for Oxígeno is effectively `shared_persona_prompt` — the
  engine is still og118/fi-runner; only the persona source is now an SSOT.
- **Follow-up (Bernard's go, separate repo):** discord-bot adopts the same
  `vultur.core.md` + its Khimeras context block. Cross-repo consumption (publish a
  `fi-personas` package, or a git submodule) is decided when that work starts;
  until then og118 is the canary proving the SSOT shape.

### Phase 2 — explicit binding type (deferred)

Promote `engineBinding` from an implicit convention to declared `fi-core` types,
once a second binding kind actually exists. Until then, adding the types is
speculative generality.

### Phase 3 — `external_http_engine` (deferred, only on real need)

Build it ONLY if Vultur (or another persona) gains capabilities that genuinely
cannot be moved under og118: exclusive tools, curated memory, own pipelines, the
Discord community as live context. Then the engine speaks a **strict FI contract**,
not an improvised bot API:

- Request accepts: `conversation_id`, `user_id`/`account_id`, `element_id`,
  `history`, `current_message`, optional `project_context`, `trace_requested`,
  `locale`, `safety_profile`.
- Response is a normalized FI stream: `element`, `text`, `declare_plan`,
  `step_started`, `step_done`, `tool_call`, `tool_result`, `result`, `error`.
- Security: service-to-service auth, caller allowlist, short timeout, per-user
  isolation, redacted logs, no arbitrary tools, no raw secrets.
- Fallback: on engine failure og118 shows a clear error and may offer "use og118
  base" — it never silently swaps to a different local persona.

## The decision that stays Bernard's

Phase 3 is a fork only Bernard opens: whether Vultur has irreplaceable runtime
capabilities that justify an external engine at all. If it never does, the SSOT
(Phase 1) is the whole fix and `external_http_engine` stays a documented option,
not built.
