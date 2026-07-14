# This repo is write-only toward the database — every read lives in the front

Repo rule for `aire-server`, registered 2026-07-13 by Bernard's directive. This is
the repo that gets cloned to the daemon's body. Toward Postgres it **only appends**.

## The law

1. **No read operations on the database in this repo.** No `SELECT` for rendering,
   analytics, browsing, dashboards, or debugging tools. The daemon holds the pen
   ([[log-is-the-truth]]); it never holds the menu.
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

## The one sanctioned exception (when the engine wakes)

The SDK's `session_store` protocol requires `load()` for `resume` — the agent
reading **its own memory** to continue a session. That is not a waiter read (it
serves no view); it is part of the write path's contract with the SDK, and it is
the ONLY read this repo may ever perform. If Bernard vetoes even this, resume
moves out of scope — his call, flagged when the engine phase starts.
