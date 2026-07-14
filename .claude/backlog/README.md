# Backlog — AIRE front

## The credential (the only one that matters today)

| # | Item | Status |
|---|------|--------|
| **1** | **A read-only Postgres role.** The app connects as `aire` — the pen's own credential, which CAN write. Four walls in `lib/db.ts` stop it, but the honest posture is a credential that simply lacks the privilege: `CREATE ROLE aire_reader … GRANT SELECT`. Needs the server admin (`devadmin` on `development-pg-n66dz`); `aire` has `rolcreaterole = false` (verified). **The day it lands, `npm run attack` must still pass with the four walls deleted** — that is the proof the fix is real. SQL in [`.claude/rules/read-only-waiter.md`](../rules/read-only-waiter.md). | **Proposed — blocked on the admin credential** |
| 2 | ~~Clean up the garbage row a failed security test left in production (`aire_log`, `seq 2641`, `'pwned'`).~~ **Dropped 2026-07-13 by Bernard: the row stays.** The law is append-only — *to correct is to append, not to erase* — and deleting the evidence of the day the lock failed would be the first mutation of a log that has never been mutated. It survives as an honest scar. (The monster does not even render it: a one-token line does not classify as an event.) | **Dropped — on purpose** |

## The console

| # | Item | Status |
|---|------|--------|
| 3 | Deploy to Azure Container Apps (image + secret + ingress). Runbook written, never run. | Proposed |
| 4 | `claude_session_store` will not be readable as a flat table — the `entry` column is JSONB holding the SDK's transcript. When the engine wakes and the table appears, it needs a real view: the conversation, rendered, not a grid of blobs. This is `aire-server`'s `render.transcript()`, re-implemented on the read side. | Proposed |
| 5 | Auth. There is none. The console exposes the whole database to anyone who reaches it — fine on localhost, **not fine with public ingress**. Blocking for #3. | Proposed |
| 6 | Sessions browser: list by `project_key`, open one, read it. Depends on #4. | Idea |
| 7 | The monster over a million rows: it currently pulls the entire log into memory to build the DFG. At `aire_log`'s current growth (~1 row/s) that is fine for months and wrong eventually — the counting belongs in SQL (`lag()` over the classified events). | Idea |

## Notes

- The backlog for the daemon (the engine, the tracer, the broom) lives in
  `aire-server/.claude/backlog/`. This one is only about the read side.
- Item #15 of that backlog — *"the front repo"* — is what this repo IS. It can be
  marked Done there once this deploys.
