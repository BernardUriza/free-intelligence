# Workflow Rules

> **Name disclaimer (post-purga 2026-07-14 + host cutover 2026-07-15)**: the
> live Container Apps are **`persona-gateway`**, **`persona-runner`** and
> **`khimeras-host`**; legacy `discord-bot` is scaled to zero and `alice-bot`
> no longer exists. See `.claude/rules/architecture.md` § Nomenclature for the
> verified table.

## Demux Progress Tracker — keep the HTML checklist in sync

The living roadmap toward the post-demux monorepo is an HTML checklist at
`~/Documents/proyectos-docs/khimeras-demux-checklist.html` (moved there from the
Desktop by Bernard; still a visible, non-dot folder per
`.claude/rules/artifact_delivery.md`. Verified 2026-09-23: the Desktop copy no
longer exists — `mdfind` is how it was found again; do not recreate it there).

**Every time work lands that advances (or changes) any item on that roadmap,
update the HTML in the same turn.** "Lands" means merged/deployed/validated —
not just started. Update means:

- Set `checked` on the `<input>` of completed items (edit the file directly;
  user-toggled state lives in localStorage and takes precedence, so editing
  the HTML never clobbers Bernard's manual checks).
- Add new checklist items when new work is discovered or scoped (new PRs,
  new gates from the coagent, new decisions), in the phase where they belong.
- Update phase tags (`EN CURSO` / `GATED` / `FUTURO` / `DONE`) and the note
  blocks when a gate opens, closes, or changes owner.
- Keep the target-tree block at the top in sync if the agreed structure
  evolves.

Scope: anything touching facts dedup (PR-1/2/3), the import-boundary ratchet,
the internal reshaping of `insult/`, the physical demux (`personas/`,
`demux_ai/`, `persona_core/`), shared/fi-core promotion, or infra/deploy
alignment. If a turn ends with one of those advanced but the HTML untouched,
the turn is incomplete.

Registered 2026-06-11 at Bernard's request ("cada que avances en algo
actualizas ese html") right after the checklist was created.

## What to do next — read the checklist, never ask

**NEVER ask Bernard "¿qué sigue?" / "what's next?" / "what do we attack?"**
The checklist at `~/Documents/proyectos-docs/khimeras-demux-checklist.html` IS
the answer (together with `.claude/backlog/README.md`, which is audited more
often — when the two disagree, the backlog's dated receipts win and the
checklist gets refreshed in the same turn).

When a work session ends or the current task completes:
1. Read the checklist — open it, scan unchecked items top-to-bottom.
2. Identify the next unchecked item that has no explicit gate blocking it
   (gate = coagent hold, explicit "GATED" tag, or a dependency on an
   unfinished predecessor).
3. Start that item. Announce the plan, execute.

The checklist is maintained in real time (rule above). It reflects the
current agreed roadmap. Bernard does not need to relay it — it is always
available and always current.

This rule was registered 2026-06-12 after Claude ended a turn with
"¿qué atacamos?" when the next unblocked item was visible in the HTML.

## CI Pipeline
4 layers in GitHub Actions, all must pass on every push/PR:
1. **Ruff Lint & Format** — fastest, runs first, blocks everything else
2. **Tests + Coverage** — pytest with the `fail_under = 75` gate from pyproject.toml
3. **Dependency Audit** — pip-audit scans for CVEs in dependencies (ignores
   reviewed in `.claude/backlog/cve-exploitability-review.md`)
4. **Code Security** — bandit SAST for Python security issues

### Running CI Locally
```bash
conda run -n discord-bot ruff check .
conda run -n discord-bot ruff format --check .
conda run -n discord-bot pytest -v --cov
conda run -n discord-bot bandit -r persona_gateway/ demux_ai/ persona_core/ shared/ -c pyproject.toml
conda run -n discord-bot pip-audit
```

### When CI Fails
- Ruff lint: run `ruff check --fix .` to auto-fix, then `ruff format .`
- Coverage below 80%: add tests for uncovered code, or add module to omit list in pyproject.toml if it's pure I/O
- pip-audit: update the vulnerable dependency
- bandit: fix the security issue or add to skips in pyproject.toml with justification

## Git Workflow
- Main branch: `main`
- Always run tests locally before pushing
- Commit messages: imperative mood, explain what and why
- One logical change per commit

## Version Bumping
- On every commit, bump the patch version (micro point) in BOTH live files
  (`personas/insult/__init__.py` died in 2f8d9ad):
  - `pyproject.toml` → `version = "X.Y.Z"`
  - `persona_core/version.py` → `VERSION_TAG = "ᵛX·Y·Z"` (superscript
    unicode — every persona's last chunk wears this same deploy tag)
- The version tag appears at the bottom of every bot response so we can track which deploy is responding
- Bump patch (Z) for fixes/small changes, minor (Y) for features, major (X) for breaking changes

## Development Flow
1. Make changes
2. Run `ruff check . && ruff format .` (lint + format)
3. Run `pytest -v --cov` (tests + coverage)
4. Commit and push
5. Watch CI: `gh run watch --exit-status`

## Python Version
- Runtime: Python 3.14 (pinned in `.python-version`)
- CI tests only on 3.14

## Session Continuity — Don't Re-Litigate Priority
- When the prior session has already identified a critical bug, regression, or load-bearing issue, the next turn STARTS work on it. Do not open a "what should we attack first?" menu, do not enumerate alternatives like `1. fix the critical / 2. commit WIP / 3. other`, and do not ask for permission to begin.
- Surfacing options is bureaucratic friction when the priority is unambiguous. It signals lack of judgment and wastes the user's time.
- Correct behavior: open with the plan, then execute. Show the plan AS you start the fix, not before. Use TaskCreate if multi-step.
- The "what's next?" question is only legitimate when there is genuine priority ambiguity — multiple equally weighted critical items, no recent context, or an explicit user pivot. Otherwise, work.
- This rule was registered after a `/work` invocation re-asked priority on a session that had just diagnosed a grave blob-download race condition losing longitudinal facts. The user's response was unambiguous: stop asking, start working.

## CI/CD Must NOT Mutate Production Data — RESOLVED (Postgres, 2026-05-13)

**The root cause was fixed**: the data plane moved out of the container to
Azure Database for PostgreSQL (see [[project_postgres_live_v3_8]]). Containers
are stateless; a deploy/revision swap touches nothing user-visible. The old
SQLite-in-container + blob backup/restore loop — whose restore race destroyed
14 minutes of a live CV-disclosure conversation on 2026-05-12
([[project_blob_download_race_bug]]) — died with the migration, and the
pre-push "is the bot mid-conversation?" band-aid check died with it.

The standing lesson: a stateful service whose deploys can mutate user data is
an architectural failure, not a race to work around. Bernard, 2026-05-12: *"el
cicd nunca deberia afectar esto… eso es vibecoding puro, no cicd."* Any future
stateful surface in this repo starts with its data plane OUTSIDE the compute.

### Sub-rule: NO band-aid menus when the user asks for architecture

When the user describes the problem in architectural terms ("CI/CD
should not mutate the DB", "the deploy should not require pausing
the conversation", "the volume mount should happen automatically"),
**do not respond with a menu of band-aids** ("option A: wait for
pause; option B: deactivate revision for 3 min").

A menu of band-aids is what an assistant who wants to close the
turn produces. A real fix is what an engineer produces. The user
is asking for the second. Match the level.

**Signs you are about to offer band-aids instead of architecture:**

- You are listing two or more "work-arounds" with trade-offs framed
  as if the user must accept one of them.
- The cheapest option still leaves the root cause in place.
- The "fix" requires the user to babysit (pause, wait, coordinate).
- The shape of the proposal is "you choose A or B" rather than
  "I do X and the problem is gone".

**When this fires, stop typing the menu and do the architecture
instead.** For the DB-during-deploy case specifically, the
architecture is: move the data plane to a managed external service
(Azure Database for PostgreSQL Flexible Server, RDS, Cloud SQL).
Container becomes stateless. Rolling updates work natively. Cero
pause. Cero downtime. Cero pérdida.

Cost is higher than SQLite-in-blob. That is the trade. If the user
has already said "no tengo limitaciones de budget", the trade is
already accepted. Don't re-litigate it as part of a band-aid menu.

This sub-rule was added on 2026-05-12 after the assistant offered
two work-arounds (pause >10min vs deactivate 3min) when the user
had explicitly asked for the proper architectural fix and removed
the budget constraint. The user's exact words: *"dos caminos de
mierda... por qué me estás ofreciendo dos opciones, una que es
pausar y otra que es apagar, cuando está la opción de hacer las
cosas bien"*.
