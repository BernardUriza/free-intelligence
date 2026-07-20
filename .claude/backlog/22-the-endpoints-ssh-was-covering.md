# The endpoints SSH was covering

Status: Proposed
Proposed: 2026-07-20 by Bernard (from the caught SSH bypass)

## What it is

Two capabilities that were exercised over `ssh` on 2026-07-20 because the AIRE
door does not offer them. Per [[ssh-is-a-missing-endpoint]], each SSH reach is a
diagnostic naming a missing endpoint — these are the two it named.

**22a — Launch a LONG job without holding the connection.** Today
`POST /projects/{p}/sessions/{s}/messages` streams SSE for the whole turn: a
20-minute book-writing job means a 20-minute open socket, and a dropped client
loses the stream (that is why `tmux` was reached for). Needed: fire-and-forget
submission returning a job handle, plus a way to ask how it is going and to
re-attach to the event stream of a job already running.

**22b — Fetch a casita's artifacts.** The agent writes real files into
`workspaces/<project>/` and there is no way to get them out over HTTP — `scp` was
used to rescue the two books. Note the wrinkle: the front cannot help here, since
these are FILES on the droplet's disk, not database rows, so this is not a
waiter read and does not belong to `front/`. It is the daemon's own surface.

## Canonical path to reuse (Art. 6)

- 22a: the SDK already streams; the pattern is the engine's existing
  `run_stream` writing to the store while an SSE endpoint replays from it —
  the log is already the source of truth ([[log-is-the-truth]]), so "re-attach"
  is a read of what the pen already wrote, not new machinery.
- 22b: FastAPI's `FileResponse`, gated by the same `AIRE_AUTH_TOKEN` door, with
  `names.clean()` guarding the path exactly as the message endpoint does.

## The decision that's the owner's

**Does artifact retrieval fit AIRE's definition, or is EC-GPS fidelity the
answer?** `CLAUDE.md` decision #3 says artifacts are fetched BY HAND for analysis
and calls that the design, not a gap — the workdir is scratch. So 22b may be a
deliberate non-feature, and `scp` may be the correct answer forever. Bernard's
call: if he keeps it, the rule's SSH-carve-out grows one line (artifacts are
fetched by hand, by a human); if he wants it, it becomes an endpoint.

Also his: whether 22a's long-job handle justifies a jobs table, or whether the
session itself is the handle (a session is already addressable, and its
transcript already records progress).

## Status / next step

Not built. Unblocked by Bernard picking the 22b fork; 22a can proceed on its own.
