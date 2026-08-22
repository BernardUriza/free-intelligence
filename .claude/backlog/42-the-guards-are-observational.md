# The guards ride observational — the buffered fork is archived, not lost

Status: **Done (observational half), the buffered half Proposed**
Proposed: 2026-08-22 by Bernard (`/ultra-lord`, "cablear ahora")

## What it is

fi-runner owned two things AIRE did not: a deterministic safety net that runs on
every turn regardless of what the model decided, and a post-turn mutation chain
where each stage declares the damage it may not do. Both came up here (`cab14b0`,
`479c1cc`) as `guard_registry` + `guard_exec` + `guard_drift` + `pipeline` +
`invariants` — copied and stripped, never imported, because fi-core is not on
PyPI and the droplet may not depend on a repo another agent edits.

The door now accepts `{"guards": ["antidrift"]}` and emits a `guards` SSE event
after `result`, carrying what each guard found.

## The decision, and the fork it closes

**AIRE streams `text` events as they arrive.** By the time a guard sees a
finished turn, the caller has already read those bytes. So the transformational
half of a guard cannot act here: a `text_override` cannot un-send what shipped,
and a `retry` would re-bill a turn nobody asked twice for.

Both are therefore **reported, never applied** — under `unenforced` and
`wanted_retry` in the event. That asymmetry is the whole point: a safety net
whose findings vanish is worse than no net, because the drift stops being
visible. `guard_exec.observe` is where that contract lives, and
`tests/test_guards_door.py` pins that nothing is silently swallowed.

Two consequences, both deliberate:

- **`background: true` + `guards` is a 422.** A detached turn has no stream to
  carry the findings, so honouring it would mean building the guards and
  discarding what they saw — a request accepted and quietly unserved.
- **Guards are built at the DOOR, not mid-turn** (`intake.safe_guards`), before a
  dollar is spent. A guard imports its backing lazily, so a missing one would
  otherwise surface as findings that never arrive. Absent backing is a 503 with
  a reason, and the droplet has no fi-core today — so `antidrift` answers 503
  there until fi-core is published or its detectors are vendored.

**Guards are NOT part of `TurnSpec`.** The spec binds the pooled client at birth,
and a guard has zero effect on the SDK client — putting them there would retire
and rebuild a live client every time a caller changed its guard list, for nothing.

## The buffered fork (Proposed, not dead)

The alternative was: when a turn requests guards, the door buffers the text and
releases it at the end, so `sanitize` and `retry` really act. It was not chosen
because it changes the SSE contract *depending on the request body* — the same
endpoint would stream for one caller and not for another, and og118 consumes that
stream in production today. If a caller ever genuinely needs a sanitized answer
more than a live one, this is the design to revive, and it should be an explicit
mode (`guards_mode: "buffered"`), never an implicit consequence of asking for a
guard.

## The decision that's the owner's

- Whether `fi-core` gets published to PyPI (so `antidrift` works on the droplet),
  or its persona detectors get vendored into AIRE the way the engine was.
- Whether the buffered mode is ever worth the split contract.

## Status / next step

Observational wiring shipped and verified. Known gap, measured 2026-08-22 and NOT
fixed here because Insult consumes those packs in production: **no fi-core pattern
pack catches a Spanish AI-disclosure leak** — *"Como modelo de lenguaje de IA, no
puedo opinar"* scores zero hits across all twelve packs, including
`GENERIC_AI_DISCLOSURE_ES`. The English equivalent is caught. Until that is fixed
upstream, `antidrift` is an English-only net.
