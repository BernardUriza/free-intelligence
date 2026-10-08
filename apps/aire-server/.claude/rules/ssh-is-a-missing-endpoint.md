# Reaching for SSH is the tell of a MISSING ENDPOINT — build the endpoint, then use it

Repo rule for `aire-server`, registered 2026-07-20 by Bernard's directive, from a
caught violation (below). AIRE exists so that **apps stop calling
`api.anthropic.com` and call AIRE over HTTP**. An agent that drives the daemon by
`ssh` + `tmux` + the `claude` CLI is not using AIRE — it is bypassing it, and
every bypass hides the exact gap the product was built to close.

## The formula (Bernard's words: *"es muy fácil la fórmula"*)

> **I need something from SSH that does not exist in the API → I create the new
> endpoint and I use it.**

That is the whole rule. SSH is not a tool for driving AIRE; SSH surfacing in your
plan is a **diagnostic** telling you which endpoint is missing.

## The prohibition

1. **NEVER drive a session through the SSH door to accomplish what the AIRE door
   should do.** No `ssh … claude -p "<prompt>"`, no `tmux new-session` wrapping
   the CLI to run a job, no `--resume` over SSH as a substitute for
   `POST /projects/{p}/sessions/{s}/messages`. Sending work through the CLI
   because it was faster than building the endpoint is the violation.
2. **The gap becomes a backlog item the same turn you hit it** — named, with the
   verb/endpoint it needs. An un-filed gap is a bypass that will repeat.
3. **Verified through the real door.** A capability is not shipped because the
   code exists: it is shipped when a `curl` from OUTSIDE the droplet exercised it
   and its memory landed in Postgres (Art. 2). Reporting a feature as working off
   an SSH run is a fake-green about AIRE itself.

## What SSH IS still for (the boundary)

The SSH door is **not** dead — the README's "two doors" stands, and one of them
is a human's:

- **Bernard at the terminal.** The interactive `claude` TUI in tmux is the
  "my Mac, but in the cloud" experience, and the droplet is deliberately his
  Linux curriculum (`systemctl`, `journalctl`, a real bound port). A human
  sitting in the terminal is the door working as designed.
- **Operating the box as a box**: reading `aire.log`, checking a unit, a
  provision run, a diagnosis. That is sysadmin work, not agent work.

The line: **SSH may operate the BODY; it may never be how you talk to the
BRAIN.** The moment the SSH command contains a prompt, you are on the wrong side
of it.

## Why (2026-07-20, the caught violation)

Asked to run two agent jobs on the droplet (the ants' volume 2, a new book about
the transistor), I did all of it over `ssh` + `tmux` + `claude -p` — including
the `--resume`. Only the `MKDIR` verb and the mirror were really AIRE. When
Bernard asked point blank — *"¿con API y curl o hiciste trampa con el ssh?"* —
the honest answer was: trampa. I had taken the path that already had code running
instead of exercising the door AIRE exists to have (the playbook's
*"la fricción disfrazada de principio"*: the choice that lets me reuse more and
build less is suspect precisely because it is cheaper).

Bernard's verdict turned the failure into the formula: *"qué bueno que hiciste la
trampa, porque ahora ya sabemos exactamente el antipatrón… si es necesario usar
el SSH, entonces lo que debes crear es un nuevo endpoint."*

What the bypass hid, surfaced only once the real door was finally exercised with
`curl`:

- The HTTP door works end-to-end from the internet (SSE `text` → `result` →
  `done`, memory straight into `claude_session_store`, no mirror lag).
- **A single-sentence turn cost $0.107** — 17,375 cache-creation tokens for the
  agent's system prompt on a fresh session, even in `mode=complete`. A real
  budget fact ([[do-budget]]) that the SSH route had been hiding.
- Two genuine gaps, now filed as backlog #22: no way to launch a LONG job without
  holding the SSE connection open, and no way to fetch a casita's artifacts (I
  used `scp`).

See also [[write-only-daemon]] (the daemon's mouths are `/health` and the message
endpoint), [[device-verb-protocol]] (the port's verbs — the same formula applied
to the socket: a new need becomes a new VERB, not a shell), and the playbook's
`verify-before-assuming` Rule 1 (exercise the real contract surface, never a
proxy).
