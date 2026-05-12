# Architecture Rules

## Project Structure
- `insult/config.py` — Pydantic Settings singleton, all config via .env
- `insult/app.py` — DI container (Container dataclass), wires all deps
- `insult/bot.py` — Discord lifecycle, events, signal handling, health check
- `insult/cogs/chat.py` — on_message listener + !chat command, reactions, response chunking
- `insult/cogs/utility.py` — !ping, !memoria, !buscar, !perfil commands
- `insult/core/llm.py` — Claude API client (async) + character break retry + anti-pattern monitoring
- `insult/core/memory.py` — Longitudinal memory (SQLite, append-only) + user profiles + user facts
- `insult/core/character.py` — Break detection, anti-pattern detection, sanitization, adaptive prompt building with preset integration
- `insult/core/presets.py` — Behavioral preset system: 6 modes + 2 modifiers, rule-based classifier, prompt guidance
- `insult/core/errors.py` — In-character error responses, error classification
- `insult/core/style.py` — User style profiling (EMA, language, formality, tech level)
- `insult/core/attachments.py` — Discord attachment processing (images, text, PDFs)
- `insult/core/facts.py` — LLM-based fact extraction from conversations, prompt building
- `insult/core/flows.py` — 4-flow behavioral analysis: Epistemic Control, Adaptive Pressure, Dynamic Expression, Conversational Awareness
- `insult/core/proactive.py` — Proactive messaging (periodic check-ins based on time/activity)
- `persona.md` — System prompt for the Insult persona (root of project)
- `tests/` — pytest suite (unit + cog tests with mocked DI container)
- `pyproject.toml` — ruff config, pytest config, coverage config, bandit config

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
