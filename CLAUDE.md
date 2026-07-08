# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

This project is **conda-managed** (memory: `feedback_no_pypi_only_conda`).
Local setup:
```bash
conda env create -f environment.yml -n discord-bot   # first time only
conda activate discord-bot                            # every shell
```

All commands below assume the `discord-bot` env is active.

```bash
# Run  (post-demux: Insult is a persona package under personas/)
python -m personas.insult run              # Start the bot
python -m personas.insult db-stats         # Show memory stats
python -m personas.insult db-clean         # Clean old data

# Test
pytest -v --cov                       # All tests + coverage report
pytest tests/chat/test_chat_cog.py -v # Single test file (tests/ split: arch/ chat/ core/ integration/)
pytest -k "test_detect_break" -v      # Single test by name

# Lint & Format
ruff check . && ruff format .     # Lint + format (run before every commit)
ruff check --fix .                # Auto-fix lint issues

# Full CI locally
ruff check . && ruff format --check . && pytest -v --cov --cov-fail-under=80 && bandit -r personas/ -c pyproject.toml && pip-audit
```

**Dependency changes**: edit `environment.yml`, then `mamba env update -f environment.yml`.
Never use `pip install <pkg>` outside the explicit pip subsection — the rule
is conda-first (see memory). `fi-core` lives on the `bernardurizaorozco`
Anaconda.org channel, declared in environment.yml's channels list.

## Architecture

> **Post-demux tree (v4.21.39+)**: the flat `insult/` god-package was demuxed into
> `personas/insult/` + `personas/alice/`, a light host `demux_ai/`, and shared
> contracts `khimeras_shared/`. **Insult is now ONE persona, not the system.** The
> inline paths in the flow descriptions below are now rooted at `personas/insult/`,
> and `cogs/chat`, `core/{memory,presets,character,llm,flows}` are **packages** (not
> single files). The canonical, current structure lives in
> `.claude/rules/architecture.md` (incl. **Phase 3.5 Production Trust**: boot-zombie
> fix DEPLOYED, Discord canary CODE-READY/deploy-GATED, constitution hook, no-fake-green
> doctrines). The chat UI primitives are cross-repo: `@free-intelligence/core` +
> `fi-glass` on public npm (free-intelligence PR #245), consumed by the python-bot template.

**Nomenclature note (post-RENAME-1b / v3.9.30)**: this repo deploys to three Azure Container Apps with names that match their roles. The plumbing container is **`discord-bot`** — it batches Discord events and routes to runners, doing zero LLM work directly (the legacy direct-Anthropic client and its `LEGACY_LLM_ENABLED` flag are deleted; the agent runner is the only turn backend). The Insult persona lives in **`persona-runner`** (Claude Code Agent SDK). The ALICE persona lives in **`alice-bot`** (Azure OpenAI gpt-4.1). The ACR image artifact is still named `insult-bot:<sha>` (legacy). Full table + rationale in `.claude/rules/architecture.md`.

**Request flow**: User message → `ChatCog.on_message` (cogs/chat/cog.py) → staged turn pipeline (cogs/chat/stages.py `DEFAULT_STAGES`): memory store → LLM-router cutover gate → context build (recent 50 + 5 keyword-relevant) → preset classification (Preset Engine port: Haiku via /v1/judge with regex shadow/fallback) → behavioral guidance + knowledge assembly → `AgentRunnerClient.chat` (khimeras_shared/runner/agent_client.py → persona-runner /v1/turn; the runner rebuilds persona + facts itself and discards plumbing `system_prompt`/`tools`/`model`) → post-LLM mutation port (echo-strip, length variation, opener dedup, `[REACT:]`/`[REMEMBER:]`/`[INVITE:]` markers) → response chunked to Discord (1990 char limit) → background: emoji reactions + fact extraction via /v1/judge.

**DI container**: `app.py` creates a `Container` dataclass holding Settings, MemoryStore, AgentRunnerClient (/v1/turn), RunnerJudgeClient (/v1/judge), and Bot. Cogs receive the container via constructor. All tests mock this container (see `tests/conftest.py` for fixtures).

**Config**: `config.py` uses Pydantic BaseSettings with `.env` file taking priority over shell env vars (custom source ordering). Settings singleton is created at module import time — tests that import from `insult.core.*` modules work fine, but importing `insult.config` directly requires `.env` to exist.

**Chat flow (no prefix)**: The bot responds to ALL messages in channels (via `on_message` listener), not just `!chat`. Messages starting with `!` are ignored by the listener (handled as commands). Per-user cooldown is 15s.

**System prompt composition** (core/character.py `build_adaptive_prompt`, returns `tuple[str, PresetSelection]`):
1. Base persona from `persona.md` (loaded at startup into settings.system_prompt)
2. Time awareness context (Mexico City timezone)
3. Metadata rules (don't reproduce timestamps, speaker labels)
4. Preset behavioral guidance — one of 6 modes dynamically selected by `classify_preset()` (core/presets.py)
5. Style adaptation hints appended per-user (if profile has 5+ messages)
6. Identity reinforcement suffix for conversations >10 messages
7. User facts appended (from facts.py)

**Preset system** (core/presets.py): Rule-based classifier (zero LLM cost) that analyzes current message + last 5 messages to select a behavioral mode. 6 modes: DEFAULT_ABRASIVE, PLAYFUL_ROAST, INTELLECTUAL_PRESSURE, RELATIONAL_PROBE, RESPECTFUL_SERIOUS, META_DEFLECTION. 2 modifiers: MEMORY_RECALL, CONTEMPT. Only the selected preset's guidance is injected into the system prompt.

**Vulnerable-user overlay** (core/vulnerability.py, v3.5.4): Priority-0 branch in `classify_preset` that forces `RESPECTFUL_SERIOUS` when the user's accumulated facts cross `VULNERABLE_THRESHOLD` (score ≥4). Scoring is weighted over 6 signal groups (`named_diagnosis`, `psychiatric_medication`, `mental_health_clinician`, `hospitalization`, `chronic_comorbidity`, `self_harm_history`). When triggered, `build_adaptive_prompt` appends `_VULNERABLE_OVERLAY_PROMPT` on top of the preset guidance — mandates warmth over abrasiveness, clinician-referral language, citation of authoritative sources via `MEDICAL_WEB_SEARCH_TOOL` (allowlist: medlineplus.gov, cima.aemps.es, nih.gov, nimh.nih.gov, who.int, salud.gob.mx), and Mexican crisis hotlines (SAPTEL, Línea de la Vida) mentioned only at acute-distress points. Exists because a user disclosing CPTSD + active psychiatric treatment was receiving DEFAULT_ABRASIVE whenever their current message lacked overt crisis keywords — see `tests/test_presets_clinical.py` for the verbatim regression cases.

**Reactions** (cogs/chat.py): LLM can include `[REACT:emoji1,emoji2]` in response. Parsed before text processing, executed async in background with human-like delay (0.5-2s). Max 3 reactions. Reaction-only responses (no text) are supported.

**Channel tools** (core/actions.py): 3 tools via Claude tool_use: `create_channel` (private/topic/category), `get_channel_info` (read name+topic of current channel), `edit_channel` (change name and/or topic). All executed in background via `_execute_tool_calls`. ACTION_INTENT modifier in presets forces `tool_choice="any"`.


**4-Flow behavioral analysis** (core/flows.py): Pre-generation pipeline that runs AFTER preset selection, BEFORE LLM call. 4 flows: Epistemic Control (detects claims, contradictions, fluff → recommends epistemic moves), Adaptive Pressure (classifies user state → pressure level 1-5), Dynamic Expression (selects response shape + style flavor with anti-repetition tracking), Conversational Awareness (detects loops, deflection, performative arguing). Output injected as Layer 3.5 in system prompt. Post-generation validator checks adherence. 5 structured telemetry events per message: `flow_epistemic`, `flow_pressure`, `flow_expression`, `flow_awareness`, `flow_adherence_violation`.

**Post-generation pipeline** (OutputMutationPort, wired in `composition.py` over `core/character/` mutators):
1. `strip_echoed_quotes` / `enforce_length_variation` / `deduplicate_opener` — guardrailed mutation stages (max-shrink caps, marker preservation)
2. `strip_reactions` / `strip_remembers` / `strip_invites` — marker lifecycle (`[REACT:]`, `[REMEMBER:]`, `[INVITE:]`)
3. Character-break/anti-drift detection now lives runner-side (fi_runner antidrift guard in persona-runner); the plumbing no longer retries on breaks

**Memory** (core/memory.py over `khimeras_shared/memory/`): Append-only **Azure PostgreSQL** (`POSTGRES_URL`; the data plane moved out of the container 2026-05-13 — the SQLite-in-blob layout and its deploy race are dead). Context is built per-channel (all users see same conversation), but style profiles are per-user. `_ensure_connection()` auto-reconnects before every DB operation.

## Testing Patterns

Tests use a fully mocked DI container (`conftest.py`). To test a cog:
1. Create the cog with `mock_container` fixture
2. Call the method directly (e.g., `cog._respond(mock_message, "text")`)
3. Assert on `mock_llm.chat`, `mock_memory.store`, `message.channel.send`

Coverage threshold is 80% in CI (`workflow.md`), 75% in `pyproject.toml` (local floor). Pure I/O modules (bot.py, app.py, config.py, llm.py, memory.py) are excluded from coverage.

## Rules
Detailed rules in `.claude/rules/`: architecture, robustness, testing, workflow, persona, voice, sibling-personas. Key non-obvious rules:
- **Sibling personas (Vultur, future) run from a durable Azure Container App** (`persona-gateway`, cloned from `alice-bot`), NEVER an ephemeral local-Mac process — see `.claude/rules/sibling-personas.md`. Diagnose "sibling X no responde" by host-liveness FIRST, not the corpus.
- **Never expose "Claude"/"Anthropic"/"AI"** in bot responses — character guard auto-retries and sanitizes
- Error messages to users must be in-character (via `core/errors.py`)
- All logging via structlog, never print()
- DB write failures are logged but don't crash commands
- Preset classification logged every message for drift monitoring
- Anti-pattern drift is logged but doesn't block responses
