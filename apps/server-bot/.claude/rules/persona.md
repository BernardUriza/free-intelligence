# Persona & Character Rules

> **Post-purga (2026-07-14, 2f8d9ad):** `personas/insult/core/{presets,character,style}.py`,
> the cogs, and the layered `build_adaptive_prompt` are DELETED. Personas are
> now DNA files under `shared/personas/<id>.md` served by the persona-runner;
> the behavior engine lives in `persona_core/behavior/`. This file describes
> the live shape plus the identity doctrine that never changes.

## Identity
- The repo hosts MULTIPLE personas — Insult (abrasive, curious, relational,
  psychologically observant, challenging, occasionally warm, never bland),
  Vultur, Frugívoro, ALICE, … — each defined by its DNA file
  `shared/personas/<id>.md` and registered in `shared/personas/registry.py`.
- NEVER expose "Claude", "Anthropic", "AI", "language model" to users.
- NEVER apologize, use assistant framing, or break character.
- Error paths are neutral and in-character by design: the gateway's failure
  recovery sends "…" or a reaction, never internals
  (`persona_gateway/gateway.py::_dispatch`).

## Preset System (`persona_core/behavior/presets/`)
- 6 behavioral modes that change HOW a persona responds based on conversation
  context: DEFAULT_ABRASIVE, PLAYFUL_ROAST, INTELLECTUAL_PRESSURE,
  RELATIONAL_PROBE, RESPECTFUL_SERIOUS, META_DEFLECTION
- Modifiers: MEMORY_RECALL (fact callbacks), CONTEMPT (ultra-minimal for
  low-effort), MULTI_DOMAIN_SYNTHESIS (cross-domain conceptual moves)
- Classifier (`classify_preset`) is rule-based (regex patterns), zero LLM cost,
  runs every turn inside `guidance_for_turn` (`persona_core/guidance.py`)
- Priority: RESPECTFUL_SERIOUS always wins (safety), then META_DEFLECTION
  (identity protection)
- Only the selected preset's guidance is rendered into the per-turn
  `behavioral_guidance` sent to the runner — the model never "knows" about
  presets, it just receives the guidance
- The prose per persona per mode is CONTENT, not code:
  `shared/personas/guidance/<persona_id>/presets/*.md`

## Character Guard — historical (no live equivalent)

The regex character-guard (`core/character.py`: ~20 CHARACTER_BREAK_PATTERNS,
~16 ANTI_PATTERN_CHECKS, auto-retry with reinforced prompt → sanitize,
`strip_metadata`) **died with the monolith in 2f8d9ad** — `grep -rn
"character_break|sanitize" persona_gateway persona_runner persona_core
shared demux_ai` returns nothing. Today, identity protection rests entirely on:

1. The persona DNA (`shared/personas/<id>.md`) — including its jailbreak /
   identity-probing scenario coverage, and
2. The neutral error path (no out-of-character degradation text).

If identity leaks resurface in prod, re-introducing a post-LLM guard is a
design decision to raise with Bernard — do not assume one exists.

## Emoji Reactions (`persona_core/reactions.py` + gateway)
- LLM can include `[REACT:emoji1,emoji2]` anywhere in response
- Parsed before text processing, executed async in background
  (`add_reactions`), human-like delay
- Max 3 reactions per message; reaction-only responses (no text) supported —
  `[REACT:👀]` with no text

## Style Adaptation (`persona_core/style.py`)
- Each user gets a style profile persisted in Postgres
  (`persona_core/memory/repositories/profiles.py`)
- Profile tracks: language, formality, technical level, verbosity, emoji usage
- Updated via EMA (exponential moving average); confidence gate
  (`CONFIDENCE_THRESHOLD = 5` messages) before the profile is applied
- Language is sticky once confident: a single off-language message cannot flip
  `detected_language` (streak counter required — the 2026-05-18 lesson, see
  robustness.md)
- Adaptation is ADDITIVE — a persona adjusts HOW it talks, never WHO it is

## Prompt Architecture (live)
A persona's turn is composed from:
1. **DNA** — `shared/personas/<id>.md`, loaded by the runner as system prompt
   (`persona_runner/engine/persona_files.py` / framing)
2. **Workspace context** — the runner's workspace `CLAUDE.md`
3. **Per-turn `behavioral_guidance`** — assembled by the gateway via
   `guidance_for_turn`: preset guidance + the vulnerable-user overlay when the
   user's facts (or an acute-crisis message) cross the threshold. (El pipeline
   `behavior/flows/` fue BORRADO 2026-07-20 — cero callers vivos; sus tipos
   sobreviven en `behavior/contracts/flows.py` para el stub del router.)
4. **Context on the wire** — user facts, other-people block, relevant history,
   corpus blocks travel in the `/v1/turn` payload built by the gateway

## Modifying a Persona
- Edit `shared/personas/<id>.md` directly — the runner reads it per turn
- Mode-specific prose: edit `shared/personas/guidance/<id>/presets/*.md` —
  content files, hot-editable, no code change
- Engine behavior (classifier patterns, priorities): `persona_core/behavior/`
- After modifying DNA or the engine, run the regression suites
  (`tests/core/test_presets_clinical.py`, `tests/core/test_guidance_guardian.py`)
  — the vulnerable-user overlay has verbatim regressions protecting Alex

## Anti-Drift
- Preset classification runs (and can be logged) every turn — flag if 90%+ of
  classifications are DEFAULT_ABRASIVE
- The old drift machinery (identity-reinforcement suffix after 10+ messages,
  break auto-retry, anti-pattern regex monitoring) is historical — it died in
  2f8d9ad with no replacement; drift watching today is done by reading real
  transcripts in #general, not by regex
