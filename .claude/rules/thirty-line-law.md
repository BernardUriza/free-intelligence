# The thirty-line law — no code file over 30 lines in this repo

Repo rule for `aire-server`, registered 2026-07-19 by Bernard's directive. Scope:
**this kind of repo only** — a droplet daemon server that doubles as Bernard's
Linux curriculum. It is deliberately NOT in the engineering-playbook: other
repos are fine at larger sizes; here every file must fit in one human glance.

## The law

**No `.py`, `.sh`, or `.yml` file in this repo may exceed 30 lines** — the unit
a human brain can comprehend whole. A file over the cap is a violation to fix
by modularizing, never by compressing (no line-golfing, no joining statements
with `;` to sneak under the bar).

## How to comply (the modularization doctrine)

1. **One responsibility per file.** Extract every self-contained block (a
   verb handler, a rate limiter, a whitelist gate) into its own module named
   after what it does.
2. **Orchestrators only delegate.** The entrypoint file wires modules together;
   it holds no dense logic itself.
3. **Workflows are thin dispatchers.** A `.yml` step never inlines a bash
   program — it calls a script under `infra/` or `scripts/`, which itself obeys
   the cap by sourcing small single-purpose libs (e.g. `infra/lib/*.sh`).
4. **Max ~5 files per folder.** When a folder outgrows that, split it into
   subfolders by responsibility.
5. **Hunt reuse after extracting.** If the extracted block existed elsewhere,
   unify to one module — duplication is the smell (Art. 6).

## The one exception (Bernard may veto)

`aire/store.py` is a near-verbatim copy of the SDK's official Postgres
session-store example, kept diffable against upstream on purpose (Art. 6 —
reuse the canonical). Splitting it would destroy that diffability. It stays
whole UNLESS Bernard strikes this exception.

## Current violators (updated 2026-07-19)

~~`aire/listener.py` 521~~ — **gutted 2026-07-19** into `aire/listen/` (24
files, every one ≤30; narratives preserved in `docs/listener-doctrine.md`).
Still over: `aire/store.py` 332 (exception above) · `aire/engine.py` 321 ·
`aire/server.py` 137 · `infra/provision-do.sh` 221 ·
`.github/workflows/costwatch.yml` 123 · `demo_device.py` 99 ·
`.github/workflows/deploy.yml` 66 · `aire/sweep.py` 55. Tracked in
[`.claude/backlog/19-thirty-line-compliance.md`](../backlog/19-thirty-line-compliance.md);
new files are born under the cap.
