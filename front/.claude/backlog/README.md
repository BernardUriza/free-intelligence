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
| 4 | `claude_session_store` will not be readable as a flat table — the `entry` column is JSONB holding the SDK's transcript. When the engine wakes and the table appears, it needs a real view: the conversation, rendered, not a grid of blobs. This is `aire-server`'s `render.transcript()`, re-implemented on the read side. | **Done** — `app/claude/[key]/[session]/page.tsx` renders the transcript as Claude Code reads it, with the casita's `CLAUDE.md` folded in (`1b4c239`). Status corrected 2026-08-22: it had said Proposed since it shipped |
| 5 | **Auth.** A login PAGE + a signed session cookie (HMAC over its own expiry, keyed with the password — no session table, and changing the password kills every cookie). Server-rendered HTML, no client JS, with sign-out. Fails CLOSED (no `AIRE_CONSOLE_PASSWORD` → 503). `?next=` is validated against open redirects. `/api/health` is the one open route and no longer discloses the schema. Was HTTP Basic for one deploy — the native prompt cannot be styled, cannot be logged out of, and broke Chrome-DevTools verification outright. Password: `~/.secrets/aire-console-password.txt`. | **Done 2026-07-14** |
| 6 | Sessions browser: list by `project_key`, open one, read it. Depends on #4. | **Done** — `app/claude/page.tsx` (the folders) + `[key]/page.tsx` (its sessions) are exactly this. Status corrected 2026-08-22: it had said Idea while live |
| 7 | ~~The monster over a million rows.~~ **Done 2026-07-14 — and it was not an "Idea", it was a lit fuse.** Measured: 413 bytes of heap per row against a log growing 2,493 rows/hour → **709 MB in a 1 GB container and 235 s per view within 30 days**. Counting moved into Postgres (`lead()` + `GROUP BY`, ~50 aggregate rows on the wire, memory constant). The naive SQL classifier (one regex/line) cost 98 µs/row and would have blown `statement_timeout` in **61 hours** — so it classifies on token position instead (6.3 µs/row, 15× faster, proven identical against the live log), reads a **200k-row window**, and says so on the page. | **Done** |
| 8 | **The daemon should persist the event kind.** The front re-classifies every line on every view because `aire_log` stores only raw text. A generated column (`kind text GENERATED ALWAYS AS (...) STORED`) plus an index would turn the monster into an indexed `GROUP BY` over the WHOLE log, at any size — no window, no scan. It is DDL, so it belongs to `aire-server` (the pen), not here. | Proposed — needs the daemon |

| 9 | **The console looked like phpMyAdmin, not like AIRE.** One design vocabulary in `globals.css` (tokens, `.tile`, `.panel`+`.scroll`, `.sect`, `.crumbs`, `.when`, `.thread`+`.turn`); the sidebar and `/console` inverted so the memory comes first and the raw tables last; and — the big one — `/claude`'s transcript now uses the SAME `Turn`/`Md`/`ToolChips` card `/gateway` already had, instead of the flat `pre-wrap` wall it had been since it shipped. Defects fixed on the way: `/gateway` cut its `turns` column off-screen, its `asked` preview showed raw `<turn_context>` scaffolding (the `split()` that strips it existed and was unused), `/claude` was the only table without a `.panel`, and the monster's labels sat on top of the next node (they now point radially outward). `npm run attack` PASSED after the `lib/db.ts` additions. | **Done 2026-08-22** |

## Notes

- The backlog for the daemon (the engine, the tracer, the broom) lives in
  `aire-server/.claude/backlog/`. This one is only about the read side.
- Item #15 of that backlog — *"the front repo"* — is what this repo IS. It can be
  marked Done there once this deploys.
