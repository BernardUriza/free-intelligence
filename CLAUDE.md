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
# Run (post-purga 2026-07-14: personas/ está BORRADO; el sistema son 4 paquetes)
python -m persona_gateway run              # el turn path de Discord (todas las personas)
uvicorn persona_runner.runner:app          # el cerebro compartido (FastAPI /v1/turn)

# Test — SIEMPRE vía conda (el pytest/ruff del PATH está roto, versión incorrecta)
conda run -n discord-bot pytest -v --cov            # todo + coverage
conda run -n discord-bot pytest tests/agent/test_router_runtime.py -q  # un archivo
conda run -n discord-bot pytest -k "test_disclosure" -v                # por nombre

# Lint & Format
ruff check . && ruff format .     # Lint + format (run before every commit)
ruff check --fix .                # Auto-fix lint issues

# Full CI locally (mirrors .github/workflows/ci.yml)
ruff check . && ruff format --check . && pytest -v --cov && bandit -r persona_gateway/ demux_ai/ khimeras_shared/ shared/ -c pyproject.toml && pip-audit
```

**Dependency changes**: edit `environment.yml`, then `mamba env update -f environment.yml`.
Never use `pip install <pkg>` outside the explicit pip subsection — the rule
is conda-first (see memory). `fi-core` lives on the `bernardurizaorozco`
Anaconda.org channel, declared in environment.yml's channels list.

## Architecture

> **Post-purga (2026-07-14, commit 2f8d9ad, −37,868 líneas)**: the whole
> `personas/` package is **DELETED** — `personas/insult/`, `personas/alice/`, the
> flat `cogs/chat` pipeline, all of it. It was the "delete-me" god-package that
> had quietly become the system; today it's gone. The live system is FOUR
> packages: **`persona_gateway/`** (the Discord turn path), **`persona_runner/`**
> (FastAPI + Claude Agent SDK), **`khimeras_shared/`** (everything shared —
> memory, the behavior engine, markers, guidance, HTTP clients), and **`shared/`**
> (the persona registry + `<id>.md` DNA + per-persona guidance content). Anything
> below that still says `personas.insult` / `cogs/chat` / `ChatCog` describes the
> dead world — trust the live packages, not those names.

**Nomenclature (post-purga)**: personas run as ONE Discord bot user each, all
sharing ONE brain (the persona-runner) addressed by `persona_id`. **`persona-gateway`**
is the live host — it spins up Insult, Vultur, Frugívoro and ALICE, each on its own
token, and owns the turn path. **`persona-runner`** is the shared Claude-Agent-SDK
brain (serves every persona via `/v1/turn`). The legacy **`discord-bot`** plumbing
container is **RETIRED — scaled to zero** at the Insult cutover; do not treat it as
a live host (its FQDN is dead). `alice-bot` (legacy gpt-4.1) is superseded by ALICE
running through the gateway. ACR image artifact still named `insult-bot:<sha>` (legacy).

**Request flow** (the gateway is the turn path — `persona_gateway/gateway.py`):
Discord message → `PersonaClient.on_message` → `should_respond` (mention / own-role
mention / vocative alias gate — a persona only answers when addressed. Post-purga
(2026-07-14) EVERY persona incl. Insult is mention-gated: `aliases=[]` for Insult, so
it is @mention-only, exactly like the siblings. NO persona answers unaddressed general
chatter right now — Insult's omnipresence died with the `personas/insult` monolith and
RETURNS only when the demux_ai host (#6) owns reception and routes. The registry
(`shared/personas/registry.py`) is the source of truth for this) → `_handle`: store the
user turn to Postgres → build per-turn
`behavioral_guidance` (`khimeras_shared/guidance.py::guidance_for_turn`: loads the
user's facts, runs `classify_preset`, renders the persona's preset guidance + the
vulnerable-user overlay) → `_run_and_deliver` → `AgentRunnerClient.chat(persona_id,
behavioral_guidance)` → runner `/v1/turn` → the runner loads `shared/personas/<id>.md`
+ workspace CLAUDE.md and answers → gateway parses markers (`[REACT:]` `[RESEARCH:]`
`[AGENDA:]` `[REMIND:]` `[REMEMBER:]`), chunks to Discord (1990 char cap), and in the
background extracts facts (ADD-only merge) and fires reactions.

**The behavior engine** lives in **`khimeras_shared/behavior/`**, persona-agnostic
(it reads the USER's state, never a persona's identity):
- `behavior/presets/` — the rule-based classifier (`classify_preset`): 6 modes
  (DEFAULT_ABRASIVE, PLAYFUL_ROAST, INTELLECTUAL_PRESSURE, RELATIONAL_PROBE,
  RESPECTFUL_SERIOUS, META_DEFLECTION) + modifiers (MEMORY_RECALL, CONTEMPT,
  MULTI_DOMAIN_SYNTHESIS). Zero LLM cost.
- `behavior/flows/` — **DELETED 2026-07-20**: the 4-flow analyzer pipeline had
  zero live callers since the purga (`guidance_for_turn` only composes presets +
  overlay). The type contracts survive in `behavior/contracts/flows.py`, consumed
  by `router_runtime.py` for its neutral stub (`_neutral_flow`).
- `behavior/vulnerability.py` — `compute_vulnerability_score` over the 6 signal
  groups (named_diagnosis, psychiatric_medication, mental_health_clinician,
  hospitalization, chronic_comorbidity, self_harm_history), threshold ≥4.
- The prose each persona speaks a mode in is **content**, not code:
  `shared/personas/guidance/<persona_id>/presets/*.md` (Insult has the full
  set; a persona with no content contributes an empty block, the engine still runs).

**The guardian (`khimeras_shared/guidance.py`)** is the seam that makes the engine
matter: it classifies the turn against the user's facts and sends the result as
`behavioral_guidance` on the wire, so the persona's mode + the safety overlay
actually reach the model. **Vulnerable-user overlay**: when the facts cross the
threshold (or the current message is an acute crisis — that path never depends on
Postgres), the overlay is appended — warmth over abrasiveness, clinician-referral
language, allowlisted medical sources (medlineplus.gov, cima.aemps.es, nih.gov,
nimh.nih.gov, who.int, salud.gob.mx), Mexican crisis lines (SAPTEL, Línea de la
Vida). Verbatim regressions in `tests/core/test_presets_clinical.py` +
`tests/core/test_guidance_guardian.py`. **Fail-safe: any fault → a normal turn,
never a mute bot.**

**Memory & facts** (`khimeras_shared/memory/`): append-only **Azure PostgreSQL**
(`POSTGRES_URL`). Facts grow ADD-only — the extractor runs in the background via
`/v1/judge`, and `merge_facts_additive` unions onto the full live auto set before
`save_facts` (a raw `save_facts(subset)` is a hard-delete in disguise, the 2026-06-03
P0). Consolidation (`khimeras_shared/consolidation/`) runs by cron with a
two-layer clinical guard: the conservative judge prompt (`prompts_md/
memory_consolidator_judge.md`, "NEVER DELETE health/trauma") **plus** a code guard
(`filter_clinical_destruction`) that refuses any DELETE of a clinical fact regardless
of what the judge asked — the cluster that protects Alex.

**Model routing** (`persona_runner/routing/`): `route_for_session` picks the tier
(Haiku/Sonnet/Opus) per session from the preset + disclosure severity, with a 24h
Opus budget. **Reminders**: `[REMIND:]` persists to Postgres and the gateway's
delivery loop rings them. **Artifacts**: `publish_html_artifact` persists HTML and
the runner serves it at `GET /a/{id}` (`ARTIFACT_BASE_URL` = the runner's own FQDN;
fails loud if unset rather than minting a dead link).

## Testing Patterns

Post-castigo fixtures live in `tests/conftest.py`: the insult-era Container/cog
fixtures died with `personas/`. What remains fixtures the shared layer — a
lightweight `mock_memory` plus the Postgres-backed `pg_memory_store`
(`tests/_pg_fixture.py`, requires a local Postgres, gated by `REQUIRES_PG`).
Gateway/runner behavior is tested by calling the functions/classes directly
(`tests/agent/`, `tests/chat/`, `tests/core/`); `tests/arch/` holds the
architecture harnesses.

Coverage gate is `fail_under = 75` in `pyproject.toml` (CI runs `pytest --cov`
against that same floor). Pure I/O modules are excluded via the coverage
config in `pyproject.toml` — read it rather than trusting doc lists.

## Rules
Detailed rules in `.claude/rules/`: architecture, robustness, testing, workflow, persona, voice, sibling-personas. Key non-obvious rules:
- **Sibling personas (Vultur, future) run from a durable Azure Container App** (`persona-gateway`, cloned from `alice-bot`), NEVER an ephemeral local-Mac process — see `.claude/rules/sibling-personas.md`. Diagnose "sibling X no responde" by host-liveness FIRST, not the corpus.
- **Never expose "Claude"/"Anthropic"/"AI"** in bot responses — post-purga there is NO regex character-guard anymore; the persona DNA + neutral error paths carry this alone
- Error paths to users are neutral and in-character: turn failure → "…" send with reaction fallback (`persona_gateway/gateway.py::_dispatch`), never internals
- All logging via structlog, never print()
- DB write failures are logged but don't kill the turn
