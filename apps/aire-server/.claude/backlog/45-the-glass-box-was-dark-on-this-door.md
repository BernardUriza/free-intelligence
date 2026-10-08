# The glass box was dark on this door — `task_tracker` joins the registry

Status: **Done — vendored, registered, tested. `rag_store` is NOT this item**
Proposed: 2026-08-24 by Bernard ("haz eso", from #44's next step)

## What it is

`task_tracker` is the registry's third tenant, beside `memory` and `persona`. The
model declares a checklist and reports each step as it goes; a consumer watching
the `tool_call` stream turns those calls into a live plan a user can see. That is
the difference between a spinner and knowing what the agent is doing.

The state machine is `engine/tracker/` — vendored from fi-core, for decision #1's
reason: fi-core is not on PyPI and the droplet must not depend on a repo another
agent edits. Same precedent as #42's guard detectors.

## The two adaptations, which are why it is not a verbatim copy

- **No session id, anywhere.** Upstream's tracker is a process-wide singleton
  keyed by a `session_id` the MODEL passes on every tool call. Here the registry
  builds one tracker per session, so the scope is structural. A scope the wire can
  name is a scope the wire can cross; here it cannot name one at all.
- **No TTL store.** Upstream must evict because it outlives every session. This
  one is owned by a pooled client and dies with it — a tighter bound than any TTL,
  and no clock to get wrong.

One behavior is deliberately NOT upstream's: a garbage step index is refused
rather than coerced to `0`. Coercion would start the wrong step and report
success, which is a silent wrong answer instead of one sentence the model can act
on. Every other refusal — a settled step, an open dependency, a plan already
finished — comes back as `is_error` text for the same reason: the model is the
only party that can correct it, and it is mid-turn in a turn the caller paid for.

The tool NAMES are upstream's, exactly, because a consumer's event translator keys
on them; renaming one here would make the plan invisible on this door alone while
every test about the state machine still passed. `tests/test_tracker_tool.py` pins
that set.

## What it cost the thirty-line law: nothing

The vendored tracker did not get `store.py`'s exemption, and it did not need one.
It came in at 194 lines and reached 150 by finding the concepts that were really
separate — `specs` (where untrusted JSON stops being that), `reshape` (pure shape
math), the settle rule (a fact about a tuple of steps, so it lives with the
models) — plus one real dedup: `declare` and `replan` had been building their step
runs with two copies of the same loop, which is how a rule gets enforced on one
path and forgotten on the other.

## Why `rag_store` is not in this item

`task_tracker` is pure in-memory state, so moving it here is a copy. `rag_store`
is 2,000 lines that need an embedder and a corpus store ON THE DROPLET, where the
budget is $20/mo and the disk is 10 GB ([[do-budget]]). Where a consumer's corpus
lives is a storage decision, not a vendoring job, and it is Bernard's — so it is
not being decided by writing it tonight.

Until then, og118's Projects search does not work on the AIRE route. It no longer
LIES about it: free-intelligence #426 drops the corpus binding wherever the tools
are absent, because a turn was shipping zero MCP servers under a prompt ordering
the model to "call search_documents IMMEDIATELY".
