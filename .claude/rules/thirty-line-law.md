# The thirty-line law — no FUNCTION over 30 lines; one concept per file

Repo rule for `aire-server`, registered 2026-07-19, **amended 2026-07-20** after
an evidence hunt (below). Scope: this kind of repo — a droplet daemon server
that doubles as Bernard's Linux curriculum. Deliberately NOT in the
engineering-playbook; other repos are fine at other sizes.

## The law

1. **No function longer than 30 lines** — the unit a human brain reads in one
   glance. This is where the canon puts the comprehension cap (ESLint
   `max-lines-per-function` defaults to 50; 30 is this repo's stricter bar).
2. **One concept = one file, files ≤ 150 lines.** A module IS its concept,
   whole: `pen.py` is the pen, `roster.py` is the roster. (Pylint's module cap
   is 1000; 150 keeps a file readable in one SSH sitting.)
3. **Anti-ravioli clause: never split ONE concept across files to duck the
   cap.** Fragmenting a coherent concept into shards (`pen/state.py`,
   `pen/batches.py`, `pen/loop.py`…) is the named anti-pattern *ravioli code* /
   Ousterhout's *classitis* — each shard is legible, the SYSTEM is not. Shrink
   by extracting ≤30-line functions INSIDE the concept's file, or by finding a
   genuinely separate concept.
4. **Flat is better than nested** (PEP 20): package depth ≤ 2. A subpackage
   exists only when a concept has genuine sub-structure, not to house shards.
5. **No compression tricks** — no line-golfing, no `;`-joined statements, no
   stripped docstrings to sneak under a cap.
6. `.sh`/`.yml`: same spirit — shell functions ≤30 lines; workflows are thin
   dispatchers that call scripts; files ≤150.

## Enforcement

`scripts/check_law.py` (AST walk: function spans + file lengths) runs in the
deploy workflow — a violation fails CI before it reaches the droplet.
Grandfathered files pending refactor are listed IN the script and shrink with
backlog #19; removing an entry is part of fixing its file.

## The one exception (Bernard may veto)

`aire/store.py` is a near-verbatim copy of the SDK's official Postgres
session-store example, kept diffable against upstream on purpose (Art. 6). It
stays whole and exempt.

## Why the 2026-07-20 amendment (the evidence)

The first version capped FILES at 30 lines. Applied to `listener.py` it
produced 24 files in 6 subpackages — and Bernard smelled it within hours:
*"todo dentro del folder de listen no tiene mucho sentido."* The hunt confirmed
his instinct is the canon:

- The tiny-file excess has a name, and it's an ANTI-pattern: **ravioli code**
  (t2informatik, TechTarget) — units legible alone, system illegible together.
- **Ousterhout** (*A Philosophy of Software Design*): the best modules are
  DEEP — simple interface, substantial implementation; "classitis" is the
  disease of many shallow ones.
- Linters put the human cap on the **function** (ESLint default 50/function),
  not the file (Pylint default 1000/module).
- Modern Python services are **module-per-concern, depth 1–2** (`config.py`,
  `db.py`, `routes.py` — the FastAPI-best-practices shape).

Full citations in the 2026-07-20 session; `docs/listener-doctrine.md` holds the
listener's module map.

## Current violators (updated 2026-07-20)

`aire/engine.py` 321 · `infra/provision-do.sh` 221 (both also carry >30-line
functions). Legal now: `server.py` 137, `costwatch.yml` 123, `demo_device.py`
99, `deploy.yml` 66, `sweep.py` 55. Exempt: `store.py` 332. Tracked in
[`.claude/backlog/19-thirty-line-compliance.md`](../backlog/19-thirty-line-compliance.md).
