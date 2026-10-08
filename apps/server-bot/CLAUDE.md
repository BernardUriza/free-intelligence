# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**Since 2026-10-08 this directory is `apps/server-bot` inside the free-intelligence
monorepo** (the standalone `BernardUriza/server-bot` repo is archived; the PR and
issue numbers cited across `.claude/` still resolve there). Everything below is
relative to this directory. CI/CD lives at the monorepo root, prefixed:
`server-bot-ci.yml` (conda env, tests, pip-audit, bandit), `server-bot-cd.yml`
(GHCR images under `ghcr.io/bernarduriza/free-intelligence/server-bot/*` → Azure
Container Apps) and `server-bot-dashboard-swa.yml`. The BAIR gatekeeper is the
monorepo's `pr-gate.yml`. `.claude/rules/` here is read on demand — the monorepo
root's `.claude/rules/` is what loads automatically.

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

# Full CI locally (mirrors the monorepo's .github/workflows/server-bot-ci.yml)
ruff check . && ruff format --check . && pytest -v --cov && bandit -r persona_gateway/ demux_ai/ persona_core/ shared/ -c pyproject.toml && pip-audit
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
> (FastAPI + Claude Agent SDK), **`persona_core/`** (everything shared —
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
`behavioral_guidance` (`persona_core/guidance.py::guidance_for_turn`: loads the
user's facts, runs `classify_preset`, renders the persona's preset guidance + the
vulnerable-user overlay) → `_run_and_deliver` → `AgentRunnerClient.chat(persona_id,
behavioral_guidance)` → runner `/v1/turn` → the runner loads `shared/personas/<id>.md`
+ workspace CLAUDE.md and answers → gateway parses markers (`[REACT:]` `[RESEARCH:]`
`[AGENDA:]` `[REMIND:]` `[REMEMBER:]`), chunks to Discord (1990 char cap), and in the
background extracts facts (ADD-only merge) and fires reactions.

**The behavior engine** lives in **`persona_core/behavior/`**, persona-agnostic
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

**The guardian (`persona_core/guidance.py`)** is the seam that makes the engine
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

**Memory & facts** (`persona_core/memory/`): append-only **Azure PostgreSQL**
(`POSTGRES_URL`). Facts grow ADD-only — the extractor runs in the background via
`/v1/judge`, and `merge_facts_additive` unions onto the full live auto set before
`save_facts` (a raw `save_facts(subset)` is a hard-delete in disguise, the 2026-06-03
P0). **Nada poda los facts hoy**: el consolidador (`khimeras_shared/consolidation/`, nombre de entonces del paquete,
688 líneas + su guarda clínica `filter_clinical_destruction`, la que protegía a
Alex) se BORRÓ el 2026-08-06 junto con su job de Azure. No fue una limpieza
cosmética: el job llevaba fallando en producción desde el 2026-07-09 (3 de 3 runs
`Failed`, un 422 del `/v1/judge` contra un esquema viejo), se "congeló" el 07-15
moviéndole el cron al **31 de febrero** — una fecha que no existe — y quedó un año
luz de poder correr: entrypoint `python -m personas.insult` sobre un paquete
borrado, imagen `insult-bot:d6fa36c` pre-purga sin parches, y CUATRO secretos
vivos colgando (`postgres-url`, `discord-token`, `insult-agent-runner-token`,
`acr-password`). Un cron imposible no es un freno, es una falla escondida.
Consecuencia asumida: los facts crecen sin techo. Si se reconstruye, se
reconstruye CON su consumidor y su guarda clínica en el mismo PR — el código vive
en git (`git show <commit>^:khimeras_shared/consolidation/`).

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
Detailed rules in `.claude/rules/`: architecture, robustness, testing, workflow, persona, voice, sibling-personas, router-observability. (Las reglas de capacitación —`training-sessions`, `delegar-produce-evidencia`— y `training-contributors/` se congelaron el 2026-09-27 al terminar la colaboración con Alex; viven en git, no en el árbol.) Key non-obvious rules:
- **"La persona equivocada contestó" se diagnostica con `python scripts/router_health.py`, NUNCA leyendo turnos sueltos** — un sesgo de ruteo es invisible turno por turno por construcción (cada decisión se ve razonable) y sólo aparece al agregar. El router mandó el 97.6% de los turnos a insult durante tres semanas con CERO señales rojas. `reason=llm_x` limpio significa que el modelo lo ELIGIÓ; `router_fault`/`llm_unparseable` significa que se cayó al default — diagnósticos opuestos. Ver `.claude/rules/router-observability.md`.
- **Un contador en cero no prueba salud: puede ser una rama que no puede sonar.** `recovered_without_context` fue inalcanzable seis semanas; `effort` se calculaba y se tiraba. El arnés que cierra la clase es `tests/arch/test_routing_prompt_promises_are_kept.py` — lo que el prompt promete, el código lo provee o lo consume.
- **Sibling personas (Vultur, future) run from a durable Azure Container App** (`persona-gateway`, cloned from `alice-bot`), NEVER an ephemeral local-Mac process — see `.claude/rules/sibling-personas.md`. Diagnose "sibling X no responde" by host-liveness FIRST, not the corpus.
- **Never expose "Claude"/"Anthropic"/"AI"** in bot responses — post-purga there is NO regex character-guard anymore; the persona DNA + neutral error paths carry this alone
- Error paths to users are neutral and in-character: turn failure → "…" send with reaction fallback (`persona_gateway/gateway.py::_dispatch`), never internals. **On the host-routed path the HOST owns the failure (v4.38.0):** `/invite?wait` returns the real outcome, the host retries once and then says in its own voice who could not answer (`demux_ai/fallback.py`); the persona's "…" survives only where the host is deaf (DM, sibling `[INVITE:]`).
- All logging via structlog, never print()
- DB write failures are logged but don't kill the turn
