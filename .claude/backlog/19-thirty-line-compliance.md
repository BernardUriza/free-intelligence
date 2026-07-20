# Bring the repo under the thirty-line law

Status: In progress — `listener.py` done 2026-07-19 (521 → `aire/listen/`, 24 files all ≤30)
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

`listener.py` gutted 2026-07-19: `aire/listen/{config,applog}` + subpackages
`pen/ roster/ guards/ verbs/ net/`, orchestrator kept as the `-m aire.listener`
entrypoint; long-form comments moved to `docs/listener-doctrine.md`; smoke test
green (reports, MKDIR ACK, DENIED, REJECTED). Next: `engine.py` (321), then
`server.py` (137), `sweep.py` (55), `provision-do.sh` (221), the workflows.
