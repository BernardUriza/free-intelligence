# Bring the repo under the thirty-line law

Status: Done 2026-07-20 — every `.py`/`.sh`/`.yml` obeys the amended law
(functions ≤30, files ≤150, one concept per file); `store.py` exempt by rule.
`scripts/check_law.py` enforces in the deploy workflow.
Proposed: 2026-07-19 by Bernard

## What it is

The thirty-line law ([`.claude/rules/thirty-line-law.md`](../rules/thirty-line-law.md))
caps every `.py`/`.sh`/`.yml` file at 30 lines. Eight files predate it and violate
it (worst: `aire/listener.py` at 521, `aire/engine.py` at 321,
`infra/provision-do.sh` at 221). This item is the compliance refactor:
modularize each violator into single-responsibility modules until the whole repo
fits the cap.

## Canonical path to reuse (Art. 6)

The modularization doctrine in the rule itself (extract by responsibility,
orchestrators delegate, workflows dispatch to scripts, sourced libs under
`infra/lib/`). `aire/store.py` is exempt while the upstream-diffability
exception stands.

## The decision that's the owner's

Whether `aire/store.py` keeps its exception, and when to schedule the refactor —
it touches the live daemon and must land with the kill test green
(re-provision resurrects everything, per `device-verb-protocol.md`).

## Status / next step

2026-07-19: `listener.py` gutted to 24 sub-30-line files. 2026-07-20 AM:
Bernard smelled the ravioli; the evidence hunt (Ousterhout's classitis, PEP 20
flat > nested, linter caps live on functions not files) amended the law and
the tree was FLATTENED to one-concept-per-module (`aire/listen/`, 9 modules).
2026-07-20 PM, the final round: `engine.py` (321) → the `aire/engine/` package
(`contract options pool drain core`, story kept in `__init__`, drain verified
with a fake-client smoke); `provision-do.sh` (221) → thin orchestrator +
`infra/lib/{keys,droplet,secrets}.sh` + `infra/remote-bootstrap.sh` (the old
heredoc, now a file with ≤30-line functions). `scripts/check_law.py` fails the
deploy workflow on any violation; `server.py`/`sweep.py`/`demo_device.py` were
already legal under the amended law.
