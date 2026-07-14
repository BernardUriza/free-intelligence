# Backlog — AIRE front

## The credential

| # | Item | Status |
|---|------|--------|
| 1 | **A read-only Postgres role.** `aire_reader`: LOGIN, no SUPERUSER, no CREATEROLE, `GRANT SELECT` and nothing else — plus `ALTER DEFAULT PRIVILEGES FOR ROLE aire` so the tables the daemon creates *later* (`claude_session_store`) are covered without anyone remembering. Proven with every wall bypassed: raw `psql` as `aire_reader`, `SET TRANSACTION READ WRITE` + `INSERT` → `permission denied`. `npm run attack` now REFUSES TO RUN unless it arrived as a role that cannot INSERT, so the fix cannot be silently reverted by a stray env var. Credential: `~/.secrets/aire-postgres-readonly.txt`. | **Done 2026-07-13** |
| 2 | ~~Clean up the garbage row a failed security test left in production (`aire_log`, `seq 2641`, `'pwned'`).~~ **Dropped 2026-07-13 by Bernard: the row stays.** The law is append-only — *to correct is to append, not to erase* — and deleting the evidence of the day the lock failed would be the first mutation of a log that has never been mutated. It survives as an honest scar. (The monster does not even render it: a one-token line does not classify as an event.) | **Dropped — on purpose** |

## The console

| # | Item | Status |
|---|------|--------|
| 3 | Deploy to Azure Container Apps (image + secret + ingress). | **Done 2026-07-13** — [live](https://aire-front.greendune-53f1f4af.eastus2.azurecontainerapps.io), `insult-rg` / `prod-env` / `insultacr`, scales to zero |
| 4 | `claude_session_store` will not be readable as a flat table — the `entry` column is JSONB holding the SDK's transcript. When the engine wakes and the table appears, it needs a real view: the conversation, rendered, not a grid of blobs. This is `aire-server`'s `render.transcript()`, re-implemented on the read side. | Proposed |
| 5 | **Auth.** HTTP Basic in `middleware.ts`, failing CLOSED (no `AIRE_CONSOLE_PASSWORD` → 503, serves nothing). Guards the app rather than the deployment, so it holds under `docker run` too. `/api/health` is the one open route and no longer discloses the schema (it used to publish every table name and row count to anyone who asked). Password: `~/.secrets/aire-console-password.txt`. | **Done 2026-07-13** |
| 6 | Sessions browser: list by `project_key`, open one, read it. Depends on #4. | Idea |
| 7 | The monster over a million rows: it currently pulls the entire log into memory to build the DFG. At `aire_log`'s current growth (~1 row/s) that is fine for months and wrong eventually — the counting belongs in SQL (`lag()` over the classified events). | Idea |

## Notes

- The backlog for the daemon (the engine, the tracer, the broom) lives in
  `aire-server/.claude/backlog/`. This one is only about the read side.
- Item #15 of that backlog — *"the front repo"* — is what this repo IS. It can be
  marked Done there once this deploys.
