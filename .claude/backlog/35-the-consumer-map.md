# The consumer map — where each of Bernard's LLM callers routes, settled

Status: **Accepted** (the map is Bernard's, 2026-08-21; the fi-fleet migration it
orders is the open work)
Proposed: 2026-08-21 by Bernard

## What it is

The full roster of app consumers that call an LLM across Bernard's repos —
verified by grep on 2026-08-21, then routed by Bernard himself, consumer by
consumer. This file exists so no future session re-proposes a dead route or
re-derives the roster (Art. 7, Art. 1). App consumers first; the Bedrock-style
CLI wiring (pointing Claude Code sessions at the gate) comes LAST — his
explicit ordering.

| Consumer | Where the call lives | Bernard's routing |
|---|---|---|
| **fi fleet: og118, fenix, aurity, activist-os** (+ fi-monitor) | via fi-runner | **→ AIRE directly** — the engine door over HTTP, with AIRE's native tools (the tool registry, the memory tool; external MCP config is #12). They must NOT keep using fi-runner directly; `AIREBackend` (fi PR #408) is the transition bridge, not the destination |
| **insult** (discord-bot / persona-runner) | gateway door | Already through the gate, named (#33). Done |
| **VHouse** | `src/VHouse.Infrastructure/Services/AIService.cs` | **RETIRED 2026-08-21** (`edd3193c`, −5,243 lines: AIService, IAIService, chatbot, AIController, CQRS handlers, config; grep zero, 274 tests green). If it ever lights up, it is born calling AIRE |
| **tianguis-cmn** | `api/app/backend.py` (fi_runner) | **RETIRED 2026-08-21** (`0049cfb` + guard fix `d9c98bb`; 11 files, fi deps out of the image, deployed and verified live: `/chat/stream` 404, `/health` 200). Same born-calling-AIRE clause |
| **escucha / copiloto de llamadas** | `compras/llamadas/escucha.py` | **Stays DIRECT to Anthropic — do not point it at AIRE.** Bernard's call, verbatim rationale: it is only his own voice on his own calls, and the transcript already lands at its destination. Re-proposing this route is an Art. 7 violation |
| **cristal.cli** | `server/run.sh` | Uses LLM but **not launched yet** — nothing to route today; revisit at launch |
| **SerenityOps portfolio-spring** | `apps/portfolio-spring/start.sh` | Uses LLM but **effectively unused** (his webpage sees almost no visits) — nothing to route today |

## The roster was incomplete — measured 2026-08-22

The routing above is Bernard's and stands. What the 2026-08-21 grep got wrong is
the FACTUAL column: who actually imports `fi_runner` today. A full sweep of the
monorepo plus 12 other repos says the fleet row over-counts and the roster
under-counts.

**The fleet row over-counts.** Only **og118** and **fenix** import `fi_runner`.
`aurity`, `aurity-desktop`, `activist-os`, `fi-monitor`, `og118-landing` and
`og118-ios` have **zero** hits — they were never fi-runner consumers, so their
"migration" is a no-op. The fleet migration is two apps, not five.

**Two real consumers the map never routed** — and they are what makes
"fi-runner → zero" unreachable, not the fleet:

| Consumer | Where the call lives | Status |
|---|---|---|
| **discord-bot / persona_runner** (the Claude Code route, distinct from insult's gateway route) | `persona_runner/engine/options.py:107` (`ClaudeCodeBackend`, `capabilities`), `demux_ai/host_llm.py:30` (`CodexBackend`) | **UNROUTED.** #33 marked insult Done through the GATEWAY door; its persona/demux routes still spawn the CLI through fi-runner. Pinned to conda `fi-runner=0.11.0`, so it does not eat this source tree |
| **cristal.cli** | `server/runner.py:14` (`ClaudeCodeBackend`), editable install of `fi-runner[claude]` | **UNROUTED.** The map says "not launched yet — nothing to route today", but the import already exists and pins the package |

**og118 is flipped in production, not migrated in code.** It reaches AIRE
*through* `fi_runner.AIREBackend` — the bridge this map names "not the
destination" — and its in-repo default is still `claude-code`
(`apps/og118/server/runner.py:163`); the AIRE route is opt-in by env var. It
still imports 9 symbols from `fi_runner` at `runner.py:20-30`, plus
`fi_runner.auth`, `fi_runner.rag_store` and `fi_runner.session_stores` in
`app.py`. The production receipt (revision `og118-api--0000091`) is real; the
code-level migration has not started.

**One duplication this repo caused.** `discord-bot/persona_runner/engine/aire_backend.py`
is a vendored 367-line copy of `fi_runner/backends/aire.py`, written because the
conda channel tops out at 0.17.1 without it. Its own header says it dies when a
fi-runner >= 0.19 carrying `AIREBackend` ships. And `fi_runner/session_stores/postgres.py`
is byte-identical to this repo's `server/aire/store.py` (332 lines, diff = 5 lines
of branding) — both copies of the SDK example. AIRE holds the pen; that copy is
fi-runner's to drop once its apps stop persisting locally.

## Canonical path to reuse (Art. 6)

The engine door already carries what the fleet needs: sessions with deathless
memory, per-turn `model`/`tools`/`images` (#29), background jobs + artifacts
(#22), the memory recall tool, the cage. What migration will surface as missing
becomes endpoints ([[ssh-is-a-missing-endpoint]] formula) — the known gap
already filed is #12 (MCP/tools configured from outside, at the user layer).

## The decision that's the owner's

- The migration order within the fleet (which app goes first).
- When cristal.cli launches, its routing (default per this map: AIRE).

## Status / next step

Map settled; first orchestrated pass ran 2026-08-21 (three agents in parallel):
VHouse and tianguis-cmn retired their LLM code same-day (receipts in their rows
above). **og118's migration is wired and smoke-tested** — fi PR
[#409](https://github.com/BernardUriza/free-intelligence/pull/409):
`OG118_BACKEND=aire` selects `AIREBackend` against the engine door (default
stays byte-identical), one real turn at $0.092 landed in the `og118` casita,
27 tests green, all checks green. **MERGED and FLIPPED 2026-08-21** (Bernard's order): PR #409 merged (merge
commit — squash disallowed there), deploys green (og118 AND fenix redeployed,
fenix on the byte-identical default). Production flip on `og118-api` (og118-rg):
secret `aire-auth-token` + env `OG118_BACKEND=aire`,
`AIRE_GATE_URL=https://gate.bernarduriza.com`, revision `og118-api--0000091`.
Verified through the REAL surface: app.og118.ai (Auth0 session), a live turn at
11:04 answered "Presente." with provenance `claude-sonnet-4-5`, and the same
minute landed in `claude_session_store` project `-opt-aire-workspaces-og118`
(session `26f6075e…`, entries at 11:04:38–45, read back via `aire_reader`).
og118's memory is deathless now. Known coupling to watch: og118 rides the
droplet (SPOF) and the engine's credential rotor (#31). Next: fenix,
aurity, activist-os, one at a time. The CLI/Bedrock wiring stays parked until
the app consumers are done — Bernard's ordering, 2026-08-21.

## Receipts (moved here 2026-08-22 from the index)

og118's migration landed as fi PRs **#410–#413** (2026-08-21). discord-bot's
stage 1 — the whole fleet through the gateway door via `ANTHROPIC_BASE_URL` —
went in flight 2026-08-22, with its engine-door migration filed as stage 2.
