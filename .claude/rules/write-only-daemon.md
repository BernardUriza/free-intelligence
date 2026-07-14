# This repo is write-only toward the database — every read lives in the front

Repo rule for `aire-server`, registered 2026-07-13 by Bernard's directive. This is
the repo that gets cloned to the daemon's body. Toward Postgres it **only appends**.

## The law

1. **No read operations on the database in this repo.** No `SELECT` for rendering,
   analytics, browsing, dashboards, or debugging tools. The daemon holds the pen
   ([[log-is-the-truth]]); it never holds the menu.
2. **Every reader is a waiter, and every waiter lives in the front repo** — the
   PHP-of-EC-GPS layer, planned as a separate Next.js project (backlog #15). The
   first tenant is the monster (the DFG view), evicted from here at commit
   `f40e21a` and parked in `~/Documents/aire-front-seed/` until that repo exists.
3. **The daemon owns the DDL.** `CREATE TABLE` for what it writes lives here; the
   front treats the schema as a read-only contract. A schema change is an API
   change between the two repos — coordinate it, never surprise the reader.

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
