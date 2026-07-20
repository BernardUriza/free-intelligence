# Bring the repo under the thirty-line law

Status: Accepted
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

Not started. Next step: gut `listener.py` first (biggest violator, hottest
surface), one commit per extracted module family, deploy + verify the real
socket after each landing.
