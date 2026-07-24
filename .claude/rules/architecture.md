# Architecture Rules

## Nomenclature — the live surfaces (post-purga 2026-07-14 + host cutover 2026-07-15)

Verified live (`az containerapp list -g insult-rg`, 2026-07-19):

| Container App | State | Role |
|---|---|---|
| **persona-gateway** | LIVE (min=max=1) | The Discord turn path. One bot user per persona (Insult, Vultur, Frugívoro, ALICE…), all mention-gated, sharing ONE brain via `persona_id`. Owns marker parsing, chunked delivery, facts extraction, reminders, voice (🔊). Binds :8788 for `/invite` + health. Code: `persona_gateway/`. |
| **persona-runner** | LIVE (min=max=1) | The shared Claude-Agent-SDK brain. FastAPI `/v1/turn` (+ `/v1/judge`, artifacts at `GET /a/{id}`). Loads `shared/personas/<id>.md` as DNA. OAuth Max. Code: `persona_runner/`. |
| **khimeras-host** | LIVE (min=max=1) | The demux reception host (#6): owns reception (`HOST_OWNS_RECEPTION` → `CONFIG.host_owns_reception` in the gateway suppresses persona self-reception), routes via gpt-4.1 (Azure OpenAI), summons personas invite-only. Code: `demux_ai/`. |
| **discord-bot** | RETIRED — scaled to 0 | The legacy plumbing container (ex `insult-bot`, renamed 2026-05-14). Dead FQDN; do not treat as a live host. |
| *(alice-bot)* | DELETED | The legacy gpt-4.1 ALICE container no longer exists; ALICE runs through the gateway on the runner. |

**ACR artifact caveat:** live images are `persona-gateway:<sha>`,
`persona-runner:<sha>`, `khimeras-host:<sha>` in `insultacr.azurecr.io`; the
legacy `insult-bot:<sha>` repo name lingers as an artifact only.

**Name history (for reading old logs/memories):** `insult-bot` (the original
monolith) → renamed `discord-bot` 2026-05-14 (RENAME-1b) → demuxed into
`personas/` + runners through v4.21.x → **the whole `personas/` package deleted
2026-07-14 (commit 2f8d9ad, −37,868 lines)** → host cutover 2026-07-15. KQL for
current incidents filters `ContainerAppName_s in ("persona-gateway",
"persona-runner", "khimeras-host")`; the old names only matter for archaeology.

## Project Structure (post-purga — verified against the tree)

The live system is FOUR packages plus the host:

- `persona_gateway/` — the Discord turn path. `gateway.py` (PersonaClient:
  reception, `_dispatch`/`_handle`, 🔊 voice reaction), `boot.py`
  (bind→connect→login order, per-persona supervision), `config.py`,
  `delivery.py` (chunked send, `DISCORD_LIMIT = 1990`), `turns.py`
  (run_and_deliver + typing keepalive), `facts.py` (background ADD-only
  extraction), `ingest.py`, `routing.py`, `markers.py`, `invites.py` +
  `invite_server.py` (:8788 `/invite`, sole host post alice-bot retirement),
  `vision.py`, `voice.py`, `workers/` (agenda, reminders, research,
  reflection).
- `persona_runner/` — FastAPI + Claude Agent SDK. `runner.py`, `api/` (turn,
  judge, artifacts, ops, workspace), `engine/` (framing, options,
  persona_files, session_pool), `routing/` (model_routing, router_runtime),
  `core/` (auth, config, schemas), `workspace_renderer.py`.
- `khimeras_shared/` — everything shared: `memory/` (Postgres store +
  repositories), `behavior/` (presets, vulnerability — the behavior
  engine), `guidance.py` (the guardian seam), `facts.py`, `style.py`,
  `markers.py`, `reactions.py`, `attachments.py`, `tts.py`/`stt.py`,
  `prompts.py` + `prompts_md/`, `consolidation/`, `corpus/`, `runner/` (HTTP
  client), `persona/`, `llm/` (shared types), `version.py` (`VERSION_TAG`).
- `shared/` — `personas/` (the registry `registry.py` — source of truth for
  aliases/gating —, per-persona DNA `<id>.md`, `addressing.py`, `guidance/`
  content), `corpus/`, `logging_setup/`, `text/`, `time_context.py`.
- `demux_ai/` — the host: `host_client.py`/`host_loop.py`, `host_llm.py`
  (gpt-4.1 reception brain), `dispatch.py`, `summon.py`, `batch.py`,
  `router_budget.py`, `llm_shadow_router.py`, `prompts/`.
- `tests/` — `arch/`, `chat/`, `core/`, `integration/`, `agent/`, `shared/` +
  top-level marker/worker tests. Fixtures post-castigo in `conftest.py`
  (`mock_memory`, Postgres-backed `pg_memory_store`).
- `infra/azure/` — `runner.Dockerfile`, `entrypoint.sh`; repo root has
  `Dockerfile.gateway` and `Dockerfile.host`.
- `pyproject.toml` — ruff, pytest, coverage (fail_under 75), bandit config.

> Anything referencing `personas/insult/`, `personas/alice/`, `demux_ai/host.py`,
> `app.py` DI containers, cogs, or `python -m insult run` describes the dead
> pre-purga world.

## Production Trust / Observability (Phase 3.5)

Born from the 2026-06-13 incident: the bot died mute for 14 min while `/health`
reported `is_ready:true` (a proxy that lied). The real liveness contract is
"responds in Discord", never an internal flag.

- **Honest health** — the lesson survived the purge: the gateway binds its
  health port before Postgres/Discord (`persona_gateway/boot.py`) and reports
  real serving state; the ActivationFailed hang class was root-fixed in
  v4.22.14.
- **Discord real canary** — **RETIRED by operator decision (2026-06-21, v4.21.97/98)**: implemented and verified (LIVE 2026-06-20), then Bernard killed the cyclic `*/5` probe because of the `#canary` message noise. Deleted end-to-end (ACA Job, cog, runner, CD step, alert, action group, webhook; `#canary` purged). **Risk note (deliberate trade-off, do not silently "fix" by reviving it):** the canary was the ONLY *un-fakeable real-contract* probe — it proved the bot actually answers on the real Discord surface every 5 min. With it retired, production-trust leans on **proxies that CAN lie** (`/health`, structured logs, the CD smoke) — exactly the fake-green class the canary existed to backstop (see `verify-before-assuming.md` rigor hierarchy). If the real-Discord-surface guarantee is ever needed again, re-introduce a canary (a single self-deleting probe, lower cadence) rather than treating a `/health` 200 as proof.
- **Constitution enforcement** — `UserPromptSubmit` hook injects the 9 articles of `engineering-playbook/rules/00-constitution.md` each turn.
- **Operational rigor doctrines** (playbook) — no fake-green / total instrumentation (`observability-logging.md`); rigor hierarchy `Chrome DevTools > proxy` + fix-Chrome-don't-route-around-it (`verify-before-assuming.md`).

## Frontend / fi-glass (cross-repo)

The chat UI primitives do NOT live in this repo. They ship from `free-intelligence`
as **public npm** packages — `@free-intelligence/core@1.1.1` (agent event contract +
`applyAgentEvent` reducer) and `fi-glass@1.1.1` (the glass chat surface) — consumed by
the `python-bot` template's `web/`. Publish workflow lands via free-intelligence PR #245.

## `dashboard/` — the ops/metrics surface (NOT a parallel product surface)

`dashboard/` is the bot's **operational dashboard** (Brython + static HTML/CSS),
deployed to its own Azure Static Web App via
`.github/workflows/azure-static-web-apps-brave-ground-0c804e410.yml`
(`app_location: /dashboard`). It is a legitimate, LIVE ops surface — NOT a
forbidden parallel/disposable product surface: discord-bot is a backend bot with
NO declared Next.js `web/` in this repo (the chat UI is the cross-repo fi-glass
above), so the "no parallel surfaces" prohibition of `new-project-stack` does not
bite here. Its deploy is path-scoped (`paths: dashboard/**`) so non-dashboard
commits no longer redeploy it. If it is ever superseded, freeze it the same day
(Art. 6) — do not let it rot as an unowned surface.

## Patterns (live)

- **Mention-gated reception**: `should_respond` in `persona_gateway/routing.py`
  + `shared/personas/addressing.py`; the registry
  (`shared/personas/registry.py`) is the source of truth for aliases. Post-purga
  EVERY persona (Insult included, `aliases=[]`) is @mention-only; omnipresence
  returns only through the khimeras-host reception.
- **Guarded turn entry**: `_dispatch` wraps `_handle`; failures log + neutral
  recovery ("…" → reaction fallback), never internals.
- Settings from env (`persona_gateway/config.py`), structured logging via
  structlog (never print()).
- **Memory is append-only**: never delete, only grow ("infinite conversation");
  Azure Postgres via `khimeras_shared/memory/`.
- **Facts are ADD-only**: background extraction (`persona_gateway/facts.py`) →
  `merge_facts_additive` onto the full live auto set before `save_facts`. A raw
  `save_facts(subset)` is a hard-delete in disguise (2026-06-03 P0).
- **Behavioral guidance per turn**: `guidance_for_turn`
  (`khimeras_shared/guidance.py`) classifies the preset against the user's
  facts and ships the rendered guidance + vulnerable-user overlay to the runner
  on the wire. Fail-safe: any fault → normal turn.
- **User invariants ride EVERY turn** (`khimeras_shared/constraints.py`,
  2026-07-23): facts tagged `category='constraint'` — atheist, vegan, allergies,
  does-not-drive, estrangements — are restrictions on what may be SAID, not
  trivia competing for prompt space. They are rendered FIRST into
  `behavioral_guidance` (so the 16k truncation eats preset prose, never an
  invariant), derived from the facts the guardian already loaded (zero extra
  queries), and deduped by containment (the ADD-only store holds one invariant
  in a dozen wordings). **Why it exists:** asked about concerts, the persona
  offered Bernard a Christian-rock band — the only automatic fact channel is
  `RELEVANT_FACTS_LIMIT = 8` ranked by similarity to the ask, and no invariant
  ever resembles the topic. Backfill of pre-tag facts:
  `scripts/backfill_constraints.py` (dry-run by default, UPDATE-only).
- Emoji reactions parsed from `[REACT:]` markers
  (`khimeras_shared/reactions.py`), executed async in background with
  human-like delay; background tasks tracked in a set for lifecycle.
- Durable markers (`[REMIND:]`, `[AGENDA:]`, `[RESEARCH:]`, `[REMEMBER:]`)
  persist to Postgres; gateway workers (`persona_gateway/workers/`) deliver.
- **`[GIF: tag]`** (`khimeras_shared/gifs.py`, 2026-07-23): the persona posts a
  GIF from its OWN catalog — `shared/personas/guidance/<id>/gifs/catalog.md`,
  `tag: url` per line, hot-editable. The model emits an INTENT, never a URL: a
  tag with no entry posts NOTHING, which is the anti-hallucination guard (a GIF
  id is an opaque number the model would invent). Hosts are allowlisted. The URL
  ships as its own bare message — no version tag, no chunking — because Discord
  only unfurls a standalone URL cleanly (same sidecar shape as the host's voice
  echo). The available tags are injected into the turn guidance; without them the
  model cannot use a repertoire it was never shown. **Why a catalog and not an
  API:** Google killed the Tenor API on 2026-06-30 (no new keys since January);
  Discord's own picker now serves from Klipy + Giphy. Existing `tenor.com/view/…`
  URLs still render — the unfurl scrapes the site, which outlived the API.

## Preset System (`khimeras_shared/behavior/presets/`)
- 6 behavioral modes: DEFAULT_ABRASIVE, PLAYFUL_ROAST, INTELLECTUAL_PRESSURE, RELATIONAL_PROBE, RESPECTFUL_SERIOUS, META_DEFLECTION
- 3 modifiers (overlay on any mode): MEMORY_RECALL, CONTEMPT, MULTI_DOMAIN_SYNTHESIS
- Priority: RESPECTFUL_SERIOUS always wins (safety), then META_DEFLECTION
- Classifier (`classify_preset`) is rule-based regex, zero LLM cost, runs every
  turn inside `guidance_for_turn`: current message (primary) + recent messages
  (secondary) + user facts (for MEMORY_RECALL)
- Only the selected preset's guidance is rendered into `behavioral_guidance`
- The prose each persona speaks a mode in is CONTENT:
  `shared/personas/guidance/<persona_id>/presets/*.md` (Insult has the
  full set; a persona with no content contributes an empty block, the engine
  still runs)

## Prompts
- **The universal rule lives in the playbook SSOT: `engineering-playbook/rules/prompts-as-content-not-code.md` (P0, all repos).** This section is the discord-bot-specific instantiation; the cross-repo law is the SSOT.
- LLM-facing prompts MUST live in content files — persona DNA in
  `shared/personas/<id>.md`, guidance prose in `shared/personas/guidance/`,
  utility prompts in `khimeras_shared/prompts_md/*.md` loaded via
  `khimeras_shared/prompts.py::load_prompt(name)` — NEVER as inline Python
  strings.
- The loader is mtime-aware: editing the `.md` is picked up on the next request
  without redeploy. Call `load_prompt("<name>")` inside the function that uses
  the prompt, NOT at module level, so hot-reload actually works.
- Current `prompts_md/` set: `facts_extraction`, `image_transcript`,
  `memory_consolidator_judge`, `other_people_header`, `reminder_delivery`,
  `self_reflection`.
- Exception: ≤5-line structural fragments the prompt builder concatenates may
  stay inline — scaffolding, not content humans iterate.
- History: convention detected 2026-05-12 while debugging flat replies; the old
  `personas/insult` inline-prompt debt list died with the package in 2f8d9ad —
  do not re-accrue it in the live packages.

## Reactions
- LLM includes `[REACT:emoji1,emoji2]` in response (max 3 emojis)
- `parse_reactions()` extracts, `strip_reactions()` removes markers
  (`khimeras_shared/reactions.py`); `add_reactions()` fires in background with
  human-like delay
- Reaction-only responses (no text) are supported — powerful for dismissal/acknowledgment
- The gateway owns the full parse→strip lifecycle
  (`persona_gateway/gateway.py` / `turns.py`)

## Attachments (`khimeras_shared/attachments.py`)
- Images (png/jpg/jpeg/gif/webp): sent as base64 vision blocks; oversize images
  are resized/re-encoded to fit the cap
- Text/code extensions: read as UTF-8, injected as text blocks
- PDFs: sent as base64 document blocks
- Unsupported types: rejected with an in-character message
- `MAX_ATTACHMENT_SIZE` = 5MB per attachment; `HARD_DOWNLOAD_LIMIT` = 25MB
- Attachment content is NOT stored in longitudinal memory (only the text message)

## Dependencies

**`environment.yml` is the source of truth** (conda-first — memory
`feedback_no_pypi_only_conda`; ruff pinned `==0.11.12`, see
`feedback_ruff_version_pinned`). Do not trust dependency lists in docs; read
the file.

## Security
- .env is gitignored — NEVER commit tokens
- Required tokens validated at startup (`PersonaRuntimeConfig.from_env` /
  gateway boot fails loud per persona with `persona_gateway_no_token`)
- All user input is parameterized in SQL (no injection)
- Max attachment size enforced (5MB)
- Never expose model identity: persona DNA forbids it, and error paths are
  neutral by design (see robustness.md) — the old regex character-guard died
  with the monolith and has NO live equivalent, so the DNA + error-path
  discipline carry that responsibility alone
- CI security layers: `bandit -r persona_gateway/ demux_ai/ khimeras_shared/ shared/`
  + `pip-audit` (`.github/workflows/ci.yml`)
