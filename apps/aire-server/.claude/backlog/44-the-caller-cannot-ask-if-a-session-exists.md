# A caller had no way to ask whether a session already exists — so it replayed

Status: **Done — the route ships; the consumer half rides in free-intelligence**
Proposed: 2026-08-24 by Bernard (`/ultra-lord`, "sí, ejecutar ahora")

## What it is

`GET /projects/{project}/sessions/{session}` answers `{"session", "exists"}` —
whether this casita already holds a transcript AIRE can resume. It is six lines
in `aire/messages.py` because the read already existed: `Engine.has_session`,
which the pool has always used to decide born-vs-resume. This route only exposes
the answer to the caller who has to make the same decision one layer up.

## Why it was missing, and what the gap cost

A consumer that keeps its OWN conversation history has two ways to send a turn:
replay that history as prompt text, or hand AIRE the session id and let the
engine resume. Without this route the second option is unverifiable — a caller
cannot know whether the memory is there — so fi-runner defaulted to replaying.

Measured against the live gate on 2026-08-24, casita `og118-06de8392-…`:

| session | turn | at |
|---|---|---|
| `06de8392-…` | 1 | 01:45:45 |
| `a29060b7-…` | 2 | 01:47:13 |

Two turns of ONE chat, two sessions, and the second one's user message opened
with `"Conversation so far:\n\nUser: …"` — fi-runner's `render_transcript`. The
conversation was paid for twice per turn (once in the replayed prompt, once in
the rows AIRE stored), the persona's cache creation was re-paid on every cold
spawn, and each session was orphaned the moment the next turn began. The
`tool_use` / `tool_result` blocks a text replay cannot carry were dropped every
time — the exact thing a raw transcript exists to keep.

## The read, against [[write-only-daemon]]

It passes the rule's criterion rather than needing an exemption: the result feeds
**the machine** — a caller deciding how to compose a turn — never a human's eyes.
Same family as exception 1 (the agent reading its own memory for `resume`); this
is that read, answered one hop earlier so the caller can act on it.

It rides the Bearer like everything but `/health`: an open existence check would
let anyone enumerate which casitas and sessions this box holds.
`tests/test_session_exists.py` pins the auth, the 404 on a hostile name, and that
`/sessions/{s}/status` is not shadowed by the new route.

## The consumer half (free-intelligence)

`AIREBackend` now declares `has_durable_memory` and answers `has_session` off
this route, and `Runner._fold_history` probes that CAPABILITY instead of reading
`backend.session_store` — an attribute only the local SDK host owns, which is why
the AIRE backend could never answer yes. A door that 404s or is unreachable
answers False, so an older AIRE degrades to the old replay cost and never to a
wrong resume.

## Next

This is step 1 of thinning fi-runner onto AIRE. Step 2 is the one that unblocks
the deletion: og118 forces `capabilities = []` and `extra_mcp_servers = []` on the
AIRE route, so turning AIRE on COSTS it `task_tracker` and `rag_store`. Until
those live in AIRE's tool registry beside `memory` and `persona`, the local SDK
host cannot be deleted and the migration cannot end ([[migrations-end-with-deletion]]).
