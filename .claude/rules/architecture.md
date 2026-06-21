# Architecture Rules

## Nomenclature — Plumbing vs Runners

Post-F3 + RENAME-1b (v3.9.30, 2026-05-14) the system is three Container
Apps with names that now match their logical roles:

| Container App | Role | What it does |
|---|---|---|
| **discord-bot** | Plumbing / gateway | Listens on Discord, batches messages, stores to Postgres, picks the right runner per turn via the feature flag, parses `[REACT:]` / `[REMEMBER:]` markers, delivers chunked response. Zero direct LLM calls when `LEGACY_LLM_ENABLED=false`. FQDN: `discord-bot.nicecliff-10074f57.eastus.azurecontainerapps.io`. |
| **insult-runner** | Insult persona | FastAPI + claude-agent-sdk (Python). OAuth Max via `~/.claude/.credentials.json`. Reads `persona.md` (Insult DNA) as system prompt + `<cwd>/CLAUDE.md` as project context via `setting_sources=["project"]`. Cwd = `/data/insult-workspace`. |
| **alice-bot** | ALICE persona | Azure OpenAI gpt-4.1 path. Sibling runner, not a Claude Code agent (different model family). Passive: only fires on mention or `/invite` from Insult. |
| *(future) aurity-runner* | AURITY persona | Qwen-only third sibling per the docstring in `alice/core/llm.py`. Not implemented. |

**ACR artifact caveat:** the OCI image repo `insultacr.azurecr.io/insult-bot:<sha>` retains the legacy name. The Container App that consumes it is `discord-bot`. Renaming the ACR repo is a separate operation (not yet done — low value, would require updating every `az acr build --image insult-bot:...` line in CD).

**KQL retroactive:** logs before 2026-05-14 are filtered by `ContainerAppName_s == "insult-bot"`. Logs from 2026-05-14 onward use `discord-bot`. For queries that span the rename window, use `in("insult-bot", "discord-bot")` until the old logs roll off Log Analytics retention (~30d).

**Pre-rename history:** the plumbing container was originally `insult-bot` (it was Insult, before the runner split). After F3 cutover (v3.9.25) it became a stateless plumbing layer; the name became confusing. RENAME-1b executed the physical rename via scale-to-0 → create new → delete old, with ~30s of Discord-visible downtime.

## Project Structure (post-demux, v4.21.39+)

The monorepo demuxed from a flat `insult/` god-package into per-persona packages
under `personas/`, a light host (`demux_ai/`), and shared contracts
(`khimeras_shared/`). **Insult is now ONE persona, not the name of the system.**
The old flat `insult/...` paths below the move no longer exist.

- `demux_ai/` — light host: explicit persona selection + gpt-4.1 routing. Live modules: `host.py`, `host_llm.py` (the gpt-4.1 host-router model client, PR-4b slice 1+), `registry.py`, `__main__.py` (`python -m demux_ai run`). No longer a skeleton.
- `personas/insult/` — the Insult persona. `app.py` (DI `Container`), `bot.py` (Discord lifecycle + health), `config.py` (Pydantic Settings), `composition.py` (the only place that knows concrete implementations), `cogs/` (chat pipeline, voice, utility), `core/` (memory **package**, llm, presets, flows, facts, health_state, debug_server, siesta, backup…), `agent/`, `prompts/*.md` (hot-reloaded), `tasks/`.
- `personas/alice/` — symmetric sibling persona (Azure OpenAI gpt-4.1). Own `app.py`, `bot.py`, `config.py`, `cogs/`, `core/`, `api/`. Passive: fires on mention or `/invite`.
- `persona_gateway/` — one Discord bot user per sibling persona (Vultur…), all sharing ONE brain (the insult-runner) via `persona_id`. `gateway.py`.
- `shared/personas/vultur.md` — Vultur persona DNA (LIVE ephemeral on the Mac; destination in `personas/` TBD).
- `khimeras_shared/` — shared contracts/infra REAL, now populated and live: `memory/`, `llm/`, `runner/`, `corpus/`, `persona/`, `vectors.py`, `style.py`, `prompts.py`, `memory_consolidation.py`. Consumed by `personas/insult`, `personas/alice`, `demux_ai` (host) and `persona_gateway` — the "migrate only when 2+ consumers share the SAME contract" bar has been met (see `khimeras_shared/PROMOTION.md`).
- `shared/` — `corpus/` (animal_liberation, film_criticism), `llm/`, `logging_setup/`, `text/`, `time_context.py`.
- `tests/` — `arch/` (import-boundary ratchet at **0**), `chat/`, `core/`, `integration/`, `agent/`, `shared/`.
- `infra/azure/` — `runner.Dockerfile`, `entrypoint.sh`.
- `pyproject.toml` — ruff, pytest, coverage, bandit config.

## Production Trust / Observability (Phase 3.5)

Born from the 2026-06-13 incident: the bot died mute for 14 min while `/health`
reported `is_ready:true` (a proxy that lied). The real liveness contract is
"responds in Discord", never an internal flag.

- **Boot-zombie observability** — DEPLOYED (v4.21.44/45): honest `serving`/`healthy`/`guild_count`, boot instrumentation (`pg_pool_creating→bot_ready`), fail-fast `os._exit`, prewarm off the critical path.
- **Discord real canary** — **RETIRED by operator decision (2026-06-21, v4.21.97/98)**: implemented and verified (LIVE 2026-06-20), then Bernard killed the cyclic `*/5` probe because of the `#canary` message noise. Deleted end-to-end: the ACA Job `insult-canary`, the `canary.py` cog + `canary_probe.py` runner + `canary-job.sh`, the `cd.yml` sync step + Dockerfile COPY, the `insult-canary-heartbeat-absent` Azure Monitor alert, the `canary-ops-ag` action group, and the "Insult Canary Ops" webhook; the `#canary` channel was purged (955 → 0). **Risk note (deliberate trade-off, do not silently "fix" by reviving it):** the canary was the ONLY *un-fakeable real-contract* probe — it proved Insult actually answers on the real Discord surface every 5 min. With it retired, production-trust now leans on **proxies that CAN lie** (`/health` + `serving`/`healthy`, structured logs, the CD `/v1/turn` smoke) — exactly the fake-green class the canary existed to backstop (see `verify-before-assuming.md` rigor hierarchy + the 2026-06-13 14-min boot-zombie that `is_ready:true` masked). The boot-zombie observability below (honest `serving`/`healthy`) is the remaining live signal. If the real-Discord-surface guarantee is ever needed again, re-introduce a canary (a single self-deleting probe, lower cadence) rather than treating a `/health` 200 as proof.
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
bite here. Its deploy is now path-scoped (`paths: dashboard/**`) so non-dashboard
commits no longer redeploy it. If it is ever superseded, freeze it the same day
(Art. 6) — do not let it rot as an unowned surface.

## Patterns
- DI container via `Container` dataclass in `app.py` — all deps injected into cogs
- Cogs pattern from discord.py — commands grouped by concern (chat, utility)
- Settings singleton with Pydantic BaseSettings (env_file=".env")
- Structured logging via structlog (JSON-ready, never use print())
- Memory is append-only: never delete, only grow ("infinite conversation")
- Context is hierarchical: recent messages (50) + keyword-relevant messages (5)
- All DB operations go through _ensure_connection() for auto-reconnect
- Commands must have @commands.cooldown to prevent token burn
- Character break detection → auto-retry → sanitize as fallback
- Anti-pattern detection → log warning (doesn't block, monitors drift)
- User style adaptation via EMA (exponential moving average) with confidence gate (5 msgs)
- Preset classification via rule-based regex patterns (zero LLM cost, runs every message)
- `build_adaptive_prompt` returns `tuple[str, PresetSelection]` — caller logs the selected preset
- Emoji reactions parsed from `[REACT:]` markers in LLM response, executed async in background
- Background tasks (reactions, fact extraction) use `asyncio.create_task` + `_background_tasks` set for lifecycle management

## Preset System
- 6 behavioral modes: DEFAULT_ABRASIVE (~55%), PLAYFUL_ROAST (~15%), INTELLECTUAL_PRESSURE (~12%), RELATIONAL_PROBE (~8%), RESPECTFUL_SERIOUS (~3%), META_DEFLECTION (~7%)
- 2 modifiers (overlay on any mode): MEMORY_RECALL, CONTEMPT
- Priority: RESPECTFUL_SERIOUS > META_DEFLECTION > RELATIONAL_PROBE > INTELLECTUAL_PRESSURE > PLAYFUL_ROAST > DEFAULT_ABRASIVE
- Only the selected preset's guidance is injected into the system prompt (not all 6)
- Classifier analyzes: current message (primary) + last 5 messages (secondary) + user facts (for MEMORY_RECALL)

## Prompts
- LLM-facing prompts MUST live in `insult/prompts/*.md`, loaded via `insult.core.prompts_loader.load_prompt(name)` — NEVER as inline Python strings.
- The loader is mtime-aware: editing the `.md` file is picked up by the running bot on the next request without a redeploy or restart. Inline strings require a version bump and full deploy cycle just to change tone.
- Call `load_prompt("<name>")` inside the function that uses the prompt, NOT at module level — so the mtime check fires per-request and hot-reload actually works.
- Migration pattern when extracting an inline prompt:
  1. Create `insult/prompts/<name>.md` with the prompt content verbatim
  2. Replace the Python constant with `load_prompt("<name>")` inside the consumer function
  3. Delete the inline constant
- Exception: ≤5-line structural fragments that the prompt builder concatenates (e.g. `CACHE_BOUNDARY`, single-line headers) may stay inline — they are scaffolding, not content humans iterate.
- Existing prompt-loader users to mirror: `moltbook_outbound_draft`, `moltbook_outbound_redaction`, `moltbook_reply_to_commenter`, `moltbook_engagement_comment`, `facts_extraction`, `language_cure`.
- Known violations (technical debt — migrate when touched):
  - `insult/core/presets.py` — `PRESET_GUIDANCE`, `MODIFIER_GUIDANCE`, `_VULNERABLE_OVERLAY_PROMPT`, `_INTENTIONALITY_DIRECTIVE`
  - `insult/core/presets_llm.py` — `_CLASSIFIER_SYSTEM_PROMPT`
  - `insult/core/character/prompts.py` — inline layers of `build_adaptive_prompt`
  - `insult/core/flows/guidance.py` — shape/flavor/pressure guidance blocks
  - `insult/core/flows/prompt.py` — flow prompt assembly
  - `insult/core/summaries.py`, `image_summary.py`, `stance_log.py` — utility prompts
- Why this rule exists: prompts are CONTENT, not code. Inline Python forces escape gymnastics on quotes, hides prompt edits in code diffs, and locks editability behind redeploy. The `prompts_loader.py` infrastructure has existed since the moltbook integration — but the convention was never documented, so subsequent commits kept adding inline prompts. Detected 2026-05-12 while debugging flat replies; the most recent `_CLASSIFIER_SYSTEM_PROMPT` addition violated the convention.

## Reactions
- LLM includes `[REACT:emoji1,emoji2]` in response (max 3 emojis)
- `parse_reactions()` extracts emojis, `strip_reactions()` removes markers from text
- Reactions fire in background with human-like delay (0.5-2s initial, 0.35s between)
- Reaction-only responses (no text) are supported — powerful for dismissal/acknowledgment
- `[REACT:]` is NOT in `strip_metadata` — chat.py owns the full parse→strip lifecycle

## Attachments
- Images (png/jpg/gif/webp): sent to Claude as base64 vision blocks
- Text/code (25+ extensions): read as UTF-8, injected as text blocks
- PDFs: sent as base64 document blocks
- Unsupported types: rejected with in-character error message
- Max size: 5MB per attachment
- Multiple attachments per message supported
- Attachment content is NOT stored in longitudinal memory (only the text message)

## Dependencies
- discord.py >= 2.3.0
- anthropic >= 0.42.0
- aiosqlite >= 0.19.0
- pydantic-settings >= 2.1.0
- structlog >= 24.1.0
- typer >= 0.9.0
- ruff >= 0.11.0 (dev)
- pytest >= 8.0.0, pytest-asyncio, pytest-cov (dev)
- bandit >= 1.8.0, pip-audit >= 2.7.0 (dev)

## Security
- .env is gitignored — NEVER commit tokens
- Bot validates required tokens at startup (validate_required)
- All user input is parameterized in SQL (no injection)
- Max message length enforced before sending to LLM (4000 chars)
- Max attachment size enforced (5MB)
- Character breaks auto-detected and sanitized (never expose model identity)
- Anti-pattern drift monitored via logging (never expose assistant behavior)
- In-character errors never expose "Claude", "Anthropic", or API internals
