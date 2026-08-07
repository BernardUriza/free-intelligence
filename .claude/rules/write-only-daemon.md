# The server half is write-only toward the database — every read lives in the front

Rule for the `server/` half, registered 2026-07-13 by Bernard's directive;
**amended 2026-07-20 for the monorepo (backlog #20)**: server and front now
share ONE repo, so the CQRS wall is no longer physical-by-repo — it is
**physical-by-credential-and-pipeline**. `server/` is what gets cloned to the
daemon's body (the droplet pulls this repo; only `server/` runs there). Toward
Postgres the daemon **only appends**.

## The law

1. **No read operations on the database in this repo.** No `SELECT` for rendering,
   analytics, browsing, dashboards, or debugging tools. The daemon holds the pen
   ([[log-is-the-truth]]); it never holds the menu.
1b. **No HTML, ever.** The daemon never returns a view — not SSR, not a landing
   page, not a rendered transcript. JSON health + SSE events are its only mouths,
   and since 2026-08-07 that includes the gateway door (`/v1/*`, backlog #30),
   which only RELAYS Anthropic's own JSON/SSE byte-for-byte — it renders nothing
   and reads nothing; its mirror APPENDS raw API turns to `aire_gateway_log`
   (created as role `aire`, so the reader's default-privileges grant covers it).
   Violated once (2026-07-14: an SSR page served `load_transcript` from here);
   reverted the same hour. The front renders; the daemon speaks events.
2. **Every reader is a waiter, and every waiter lives in `front/`** — the
   PHP-of-EC-GPS layer (Next.js SSR,
   [live on Container Apps](https://aire-front.greendune-53f1f4af.eastus2.azurecontainerapps.io),
   backlog #15; merged into this monorepo from `aire-front-seed` with full
   history, backlog #20). The first tenant was the monster (the DFG view),
   evicted from the server at commit `f40e21a`.
   **Its half of this law is [`front/.claude/rules/read-only-waiter.md`](../../front/.claude/rules/read-only-waiter.md)** —
   one law, two halves, two credentials, two pipelines: `server/` only appends
   (deploy-server → droplet), `front/` only reads (deploy-front → Azure, and
   its CI attack suite proves the DATABASE refuses its role a write).
3. **The daemon owns the DDL.** `CREATE TABLE` for what it writes lives in
   `server/`; the front treats the schema as a read-only contract. A schema
   change is an API change between the two halves — now one atomic diff, but
   still coordinated, never a surprise to the reader.
4. **The pen's credential is the daemon's alone — one law, two credentials.**
   `AIRE_DATABASE_URL` here (role `aire`, `~/.secrets/aire-postgres.txt`) grants
   **write**: that is what makes it the pen. The front gets a different one —
   **`aire_reader`** (`GRANT SELECT` and nothing else,
   `~/.secrets/aire-postgres-readonly.txt`). **Never hand the front this repo's
   credential**; its own attack suite refuses to run if it ever finds itself
   holding the pen.

   This is not belt-and-braces, it is *the* wall — learned the hard way: a
   read-only **transaction mode** is not a read-only **credential**, and a role
   that can write can always take the privilege back. `SET TRANSACTION READ WRITE`
   did exactly that on 2026-07-13, defeating four walls of application code, and a
   `'pwned'` row reached `aire_log` at `seq 2641`. It is still there — the log is
   append-only, and correcting means appending, not erasing.

   **The DDL consequence, and it is this repo's job:** the reader's grant on
   *future* tables rides on
   `ALTER DEFAULT PRIVILEGES FOR ROLE aire IN SCHEMA public GRANT SELECT ON TABLES TO aire_reader`.
   It is already set. So `claude_session_store` will be readable the day the engine
   creates it — **as long as the daemon creates it as `aire`.** Create a table as
   any other role and the waiter goes blind to it.

## Why

This is CQRS applied at repo granularity, and it is the EC-GPS blueprint exactly:
the Perl daemon never read `gps_logs` to display anything; the PHP console never
wrote it. Two codebases, two deployments, one append-only table as the frontier.
Kreps's "The Log" (already this repo's law) names the log as the integration
point between the producing system and its consumers — separating the repos makes
that boundary physical.

## The sanctioned exceptions (bounded, not waiter reads)

A "read" here means a **waiter read** — a `SELECT` that serves a human-facing
view. Those all live in the front. But the write path has two reads that are part
of its own contract, not views, and are explicitly allowed:

1. **`session_store.load()` for `resume`** — the agent reading **its own memory**
   to continue a session. Serves no view; it is the SDK's write-path contract.
   The same exception has a second face since 2026-07-20: `aire/restore.py`
   (backlog #17) loads the store to RE-MATERIALIZE the door's JSONL transcripts
   on a fresh box — restore IS resume for the SSH door. Disk wins: an existing
   file is never overwritten.
2. **The device whitelist load** (`aire_device`, backlog #18) — the daemon reading
   the roster it must ENFORCE at the socket. Authorized by Bernard 2026-07-14 when
   he chose "the whitelist lives in Postgres" over a mortal file. It is not a view
   either: it gates writes, it does not display anything. The daemon owns every
   write to the table (the ALLOW/REVOKE verbs), so the read is a startup load kept
   in lockstep with those writes — no polling, no query per connection.

3. **The `memory` tool's `recall`** (`engine/memory_tool.py`, backlog #29) — the
   agent searching its OWN transcript in `claude_session_store` through a per-turn
   tool. It is the SAME family as exception 1 (the agent reading its own memory),
   not a waiter read: the result feeds the AGENT (a tool result), never a human
   view. Session-scoped by construction (the server closes over the casita's
   project_key), so one project can never read another's transcript. Authorized by
   Bernard 2026-07-29 when he chose "an in-process memory server over AIRE's own
   Postgres" as the first tenant of the tool registry.

None is a waiter read. If Bernard vetoes any, that feature moves out of scope —
his call. Any read that serves a VIEW is a violation; it belongs in the front.
