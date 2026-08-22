# The guards ride observational — the buffered fork is archived, not lost

Status: **Done — observational, vendored, live. The buffered half stays Proposed**
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
  a reason — which is exactly what `antidrift` answered on the droplet for one
  afternoon, until the detectors were vendored (below).

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

## Vendored, not published (2026-08-22, Bernard's call)

`antidrift` imported `fi_core.persona` lazily, so it answered **503 on the very
box it was built for**: fi-core is not on PyPI and the droplet installs from
`requirements.txt`. Two ways out, and the fork was real.

**Publishing fi-core to PyPI** would have given one source of truth for the packs
that fi-runner, discord-bot and cristal.cli also read — but it puts a name and a
noncommercial licence on a public index, hangs the droplet off a release
pipeline, and forces the Spanish fix upstream, where Insult runs in production.

**Vendoring** is the precedent Bernard already set for the engine, and for the
same reason in his own words: the droplet must not depend on a repo another agent
edits. It touches one repo and reverts by deleting files. That is what shipped:
`engine/drift_detect.py` (82 lines, `re` only).

Two things were pruned on the way in, because vendoring is pruning, not
photocopying:

- fi-core ships **three** detector classes whose `detect` bodies are
  byte-identical and differ only in a severity label. Copying that triplication
  into a clean repo would import a defect along with the feature — it is one
  `Detector` carrying its severity. The `check()`/`DetectionResult` surface had
  no consumer here and did not survive the trip.
- The 64 regexes are **content a human iterates**, not code:
  `prompts/drift-patterns.json`, read at call time behind an mtime cache. A tone
  fix is an edit, not a redeploy ([[prompts-as-content-not-code]]). A pattern
  that fails to compile is dropped and named on stderr — an unusable rule must
  not disarm the rules beside it.

**The Spanish gap is closed in AIRE's copy.** Six ES AI-disclosure patterns
fi-core lacks now ship here, and `test_drift.py` pins both the Spanish and
English leaks — plus three lines of Bernard's own pocho register, so the fix
cannot start eating legitimate speech.

## The decision that's the owner's

- Whether fi-core's own packs ever get the Spanish patterns upstream (that repo's
  call — Insult reads them in production).
- Whether the buffered mode is ever worth the split contract.

## Status / next step

Observational wiring shipped and verified. Known gap, measured 2026-08-22 and NOT
fixed here because Insult consumes those packs in production: **no fi-core pattern
pack catches a Spanish AI-disclosure leak** — *"Como modelo de lenguaje de IA, no
puedo opinar"* scores zero hits across all twelve packs, including
`GENERIC_AI_DISCLOSURE_ES`. The English equivalent is caught. Until that is fixed
upstream, `antidrift` is an English-only net.
