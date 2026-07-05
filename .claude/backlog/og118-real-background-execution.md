# OG118-BACKGROUND-1 — real cross-turn background execution (make "te aviso" true)

Status: Proposed
Proposed: 2026-07-05 by Bernard (dogfood: og118 promised a background investigation, then had no access half an hour later)

## What it is

og118's runtime is **request/response stateless** — each `/chat/stream` turn is a
fresh Claude Code invocation with no process that survives past the reply
(intentional: continuity is client-sent history replay, so the backend survives
ACA replica recycles — see `runner.py` DD-002C). Consequence: when the persona
enters "agent mode" and promises to *"seguir investigando en el background y te
aviso"*, there is no background — the turn ends, nothing runs, and the next turn
the model has no memory or access of the promised task.

The **honesty guard** (shipped separately) makes the persona STOP promising async
work it can't do. This item is the opposite direction: **actually support it** —
a real background job system so "te aviso cuando termine" becomes true:

- a durable task queue / worker that runs a research/analysis job across turns;
- resumable, cancellable jobs (fi-core `task_tracker` v2 already models
  DAG deps / replanning / cancellation — see the task_tracker v2 memory — but its
  EXECUTION is still within a turn);
- a way to surface "job N finished" back into the conversation (push/poll), and
  persistence that survives an ACA replica recycle (the current stateless design
  deliberately has none server-side).

## Canonical path to reuse (Art. 6)

Do NOT hand-roll a queue. Evaluate reusing: fi-core `task_tracker` v2 (plan/step
model + cancellation, already wired as an og118 capability) as the job *model*;
a durable backend for the *execution* (the open question). Whatever runs the job
must respect the same COMPANION `ToolPolicy` and corpus binding as a live turn —
the background worker is not a wider-privilege path.

## The decision that's the owner's

Whether og118 should have real background execution at all, and the architecture:
it breaks the current "stateless backend, client-owned transcript" invariant that
makes og118 survive redeploys with zero server state. A durable job store is new
server-side state (cost, ops, the ACA-recycle-safety it currently gets for free).
Bernard's call: is a genuinely-async companion worth trading away statelessness,
or is the honesty guard (never promise what you can't do) the right final answer?

## Status / next step

Not built. Blocked on the architecture decision above. The honesty guard ships
now as the correct interim behavior (no lying about async); this item captures the
real-async feature so the roadmap doesn't lose it. See [[framework-first-canary]].
