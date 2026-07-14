# This repo is write-only toward the database — every read lives in the front

Repo rule for `aire-server`, registered 2026-07-13 by Bernard's directive. This is
the repo that gets cloned to the daemon's body. Toward Postgres it **only appends**.

## The law

1. **No read operations on the database in this repo.** No `SELECT` for rendering,
   analytics, browsing, dashboards, or debugging tools. The daemon holds the pen
   ([[log-is-the-truth]]); it never holds the menu.
1b. **No HTML, ever.** The daemon never returns a view — not SSR, not a landing
   page, not a rendered transcript. JSON health + SSE events are its only mouths.
   Violated once (2026-07-14: an SSR page served `load_transcript` from here);
   reverted the same hour. The front renders; the daemon speaks events.
2. **Every reader is a waiter, and every waiter lives in the front repo** — the
   PHP-of-EC-GPS layer. **It exists**: [`aire-front-seed`](https://github.com/BernardUriza/aire-front-seed)
   (Next.js SSR, [live on Container Apps](https://aire-front.greendune-53f1f4af.eastus2.azurecontainerapps.io),
   backlog #15). The first tenant was the monster (the DFG view), evicted from
   here at commit `f40e21a` and now served there.
   **Its half of this law is [`read-only-waiter`](https://github.com/BernardUriza/aire-front-seed/blob/main/.claude/rules/read-only-waiter.md)** —
   one law, two repos: this one only appends, that one only reads.
3. **The daemon owns the DDL.** `CREATE TABLE` for what it writes lives here; the
   front treats the schema as a read-only contract. A schema change is an API
   change between the two repos — coordinate it, never surprise the reader.
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
2. **The device whitelist load** (`aire_device`, backlog #18) — the daemon reading
   the roster it must ENFORCE at the socket. Authorized by Bernard 2026-07-14 when
   he chose "the whitelist lives in Postgres" over a mortal file. It is not a view
   either: it gates writes, it does not display anything. The daemon owns every
   write to the table (the ALLOW/REVOKE verbs), so the read is a startup load kept
   in lockstep with those writes — no polling, no query per connection.

Neither is a waiter read. If Bernard vetoes either, that feature moves out of
scope — his call. Any THIRD read that serves a view is a violation; it belongs in
the front.
