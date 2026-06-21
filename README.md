# Khimeras

Multi-persona Discord bot system. One Discord-facing plumbing layer routes each
turn to a persona runner; each persona has its own DNA (`persona.md`), its own
Discord identity, and its own model family. **Insult** is the flagship persona —
abrasive, curious, psychologically observant — but it is now *one* persona, not
the name of the system.

> Post-demux monorepo (v4.21.39+). The old flat `insult/` god-package was split
> into a light host (`demux_ai/`), per-persona packages (`personas/`), a gateway
> (`persona_gateway/`), and shared contracts (`khimeras_shared/`).

## Architecture

A turn flows: **Discord message → plumbing batches & stores it → routes to the
right persona runner → runner produces the reply → plumbing chunks it back to
Discord.** The plumbing does zero direct LLM work; cognition lives in the runners.

In production this is three Azure Container Apps:

| Container App | Role | Engine |
|---|---|---|
| **discord-bot** | Plumbing / gateway — listens on Discord, batches, persists to Postgres, picks the runner per turn, parses `[REACT:]`/`[REMEMBER:]`, delivers chunked replies | none (routing only) |
| **insult-runner** | Insult persona | Claude Agent SDK (OAuth Max) |
| **alice-bot** | ALICE persona — passive, fires on mention or `/invite` from Insult | Azure OpenAI gpt-4.1 |

The OCI image artifact is still tagged `insult-bot:<sha>` (legacy name). See
`.claude/rules/architecture.md` § Nomenclature for the full table and the
RENAME-1b history.

## Repo layout

```
demux_ai/            light host: explicit persona selection + gpt-4.1 routing (host.py, host_llm.py, registry.py)
personas/
  insult/            the Insult persona — app.py (DI Container), bot.py, config.py,
                     composition.py, cogs/ (chat pipeline, voice, utility), core/
                     (memory, llm, presets, flows, facts, health…), agent/, prompts/*.md
  alice/             sibling persona (Azure OpenAI gpt-4.1) — own app/bot/config/cogs/core/api
persona_gateway/     one Discord bot user per sibling persona, all sharing one brain via persona_id
khimeras_shared/     shared contracts/infra with 2+ real consumers — memory/, llm/, runner/,
                     corpus/, persona/, vectors.py, style.py (see khimeras_shared/PROMOTION.md)
shared/              cross-cutting helpers — corpus/, llm/, logging_setup/, text/, time_context.py
tests/               arch/ (import-boundary ratchet) · chat/ · core/ · integration/ · agent/ · shared/
infra/azure/         runner.Dockerfile, entrypoint.sh
docs/                kql_queries.md, runbook_alerts.md
.claude/rules/       the binding rules (architecture, robustness, testing, workflow, persona, voice)
.claude/plans/       ADRs (demux, agent-sdk migration, capability seams, model router…)
```

## Quickstart

This project is **conda-managed** — conda-first, never `pip install` outside the
explicit pip subsection of `environment.yml`.

```bash
conda env create -f environment.yml -n discord-bot   # first time only
conda activate discord-bot                            # every shell
```

Run a surface (each persona / host has its own entrypoint):

```bash
python -m personas.insult run        # Insult bot
python -m personas.insult db-stats   # memory stats
python -m personas.insult db-clean   # clean old data
python -m personas.alice run         # ALICE bot
python -m demux_ai run               # host: select & boot a persona explicitly
python -m persona_gateway run        # gateway: sibling personas on one brain
```

Runtime: Python 3.14 (pinned in `.python-version`).

## Testing & CI

```bash
ruff check . && ruff format .                       # lint + format (before every commit)
pytest -v --cov                                     # tests + coverage
pytest tests/chat/test_chat_cog.py -v               # single file
pytest -k "test_detect_break" -v                    # single test by name

# Full CI locally
ruff check . && ruff format --check . \
  && pytest -v --cov --cov-fail-under=80 \
  && bandit -r personas/ -c pyproject.toml && pip-audit
```

CI (GitHub Actions) runs four gates on every push/PR — Ruff lint+format, tests at
80% coverage, `pip-audit`, and `bandit`. On green CI, CD builds the images and
deploys to Azure Container Apps; the post-deploy smoke runs a **real** `/v1/turn`.

## Where the detail lives

- **`CLAUDE.md`** — guidance for working in this repo (commands, request flow, prompt composition).
- **`.claude/rules/`** — the binding rules: `architecture.md`, `robustness.md`, `testing.md`, `workflow.md`, `persona.md`, `voice.md`.
- **`.claude/plans/`** — ADRs and design docs (the demux north star is `khimeras_demux_destilado.md`).
- **`docs/`** — operational: KQL queries and the alerts runbook.
- The chat UI primitives are cross-repo — `@free-intelligence/core` + `fi-glass` on public npm, consumed by the `python-bot` template's `web/`.
