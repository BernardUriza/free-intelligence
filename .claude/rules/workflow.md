# Workflow Rules

## CI Pipeline
4 layers in GitHub Actions, all must pass on every push/PR:
1. **Ruff Lint & Format** — fastest, runs first, blocks everything else
2. **Tests + Coverage** — pytest with 80% minimum coverage gate
3. **Dependency Audit** — pip-audit scans for CVEs in dependencies
4. **Code Security** — bandit SAST for Python security issues

### Running CI Locally
```bash
ruff check .                                    # lint
ruff format --check .                           # format check
pytest -v --cov --cov-fail-under=80             # tests + coverage
bandit -r insult/ -c pyproject.toml             # security code
pip-audit                                       # security deps
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
- On every commit, bump the patch version (micro point) in BOTH:
  - `pyproject.toml` → `version = "X.Y.Z"`
  - `insult/cogs/chat.py` → `VERSION_TAG = "ᵇᵉᵗᵃ ᵛX·Y·Z"` (superscript unicode)
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

## CI/CD Must NOT Mutate Production Data — MANDATORY

**Root cause first, then the band-aid.** A deploy that silently
destroys the database is not "a race condition we work around" — it
is an architectural failure that any serious CI/CD pipeline would
prevent by construction.

### The root cause that MUST be fixed

The bot stores all conversation state in a SQLite file (`memory.db`)
that lives **inside the container**. Persistence between deploys is
done via a blob-storage backup/restore loop:

1. Container running: writes to local SQLite, periodically uploads
   the file to Azure Blob Storage (~every 10 min).
2. Container restarting (deploy / scale event / health failure):
   the new replica boots, finds no local DB, downloads the blob to
   `memory.db`, and starts running.
3. The window between (1) last upload and (2) restart is **the bug**:
   any messages stored locally that haven't been uploaded yet are
   wiped when the new replica overwrites with the stale blob.

This is documented in [[project_blob_download_race_bug]] and was
discovered 2026-04-27. It is STILL not fixed as of 2026-05-12. On
2026-05-12 it destroyed 14 minutes of an active CV-disclosure
conversation between Bernard and Alex, including the only copy of
Alex's full resume that Insult had ever seen.

**This is vibecoding, not CI/CD.** A serious deployment of a
stateful service does one of:

- **Separate the data plane from the compute plane.** PostgreSQL on
  Azure Database for PostgreSQL, Cloud SQL, RDS, etc. The container
  is stateless; restarting it touches nothing user-visible. This is
  the correct fix. SQLite in a container with blob backup is
  acceptable for a hobby weekend project, not for a bot carrying
  vulnerable-user disclosures.
- **At minimum**, before any restart, force a final blob upload from
  the *outgoing* replica and block the new replica from running its
  download until the upload completes. This is still racy under
  network failure but closes the common case.

**The user explicitly called this out on 2026-05-12**: *"el cicd
nunca deberia afectar esto!? como es posible que una base de datos
se elimine o se bloquee silenciosamente durante un deploy? eso es
vibecoding puro, no cicd"*. They are right. Until the data plane is
moved out of the container, every deploy is a partial data-loss
event waiting to happen.

### The band-aid (only valid until the root cause is fixed)

Before any `git push` to `main`, check whether the bot is mid-
conversation. The CI/CD pipeline triggers a container revision swap
that can wipe up to ~15 minutes of messages on each swap.

```bash
# SAFE if no turn in the last 10 min, BLOCKED otherwise.
curl -s "https://insult-bot.nicecliff-10074f57.eastus.azurecontainerapps.io/debug/health" -m 10 \
  | python3 -c "import json,sys; d=json.load(sys.stdin); age=d.get('last_turn_age_s'); \
  print('SAFE' if age is None or age > 600 else f'BLOCKED — last turn {age:.0f}s ago')"
```

If output is `BLOCKED`, the deploy is FORBIDDEN until either:
1. The root-cause fix lands (data plane moved out of container), OR
2. The conversation pauses for >10 minutes, OR
3. The user explicitly says "deploy now, I'm OK losing messages".

**No exceptions for "small" or "urgent" fixes.** A non-blocking
prompt change is worth less than 15 minutes of a stressed user's
conversation with the bot.

**Also applies to:** Azure container revision activation/deactivation,
manual blob uploads, anything that triggers a container restart with
the blob-restore path. If you must restart in flight, use the
blob-recovery procedure (scale down → patch blob → scale up).

**Treat the band-aid as evidence of architectural debt, not as a
solution.** Every time this check runs, it is a reminder that the
data plane lives in the wrong place. The next time a non-trivial
amount of dev time is available, the priority is migrating
`memory.db` out of the container, not adding more guards around
the broken layout.

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
