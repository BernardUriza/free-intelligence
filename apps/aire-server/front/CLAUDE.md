@AGENTS.md

# AIRE front — context for agents

The **read half** of AIRE. `aire-server` holds the pen and only appends; this
repo holds the menu and only reads. One append-only table is the frontier.

Everything below was verified against the running system or the source — never
against memory. To contradict it, verify it the same way.

## The decisions, already made

1. **This repo NEVER writes to Postgres.** Not a migration, not a cache table,
   not a "quick fix". Full law:
   [`.claude/rules/read-only-waiter.md`](.claude/rules/read-only-waiter.md).
2. **Next.js SSR on Azure Container Apps.** This was Bernard's call from the
   start — `aire-server`'s backlog #15 said *"a separate Next.js project"* before
   a line was written here. An earlier attempt built this front in Python because
   the monster already was Python; that was the low-friction path wearing a
   principle's clothes, and it was deleted.
3. **The schema is DISCOVERED, never modelled.** Tables and columns come from the
   Postgres catalog at request time. The day `aire-server` creates
   `claude_session_store`, it appears in the sidebar with zero code change here.
   Never hardcode a table.
4. **`lib/db.ts` is the only module that opens a connection.** One door, so the
   walls stand in one place.
5. **No client JavaScript.** Every page is a Server Component; the forms are plain
   HTML; the monster's SVG is server-rendered markup, not a charting library.
6. **One design vocabulary, and ONE conversation card.** `app/globals.css` holds
   the tokens and the only shapes a page may reach for (`.tile`, `.panel` +
   `.scroll`, `.sect`, `.crumbs`, `.when`, `.thread` + `.turn`). A transcript is
   drawn by `Turn`/`Md`/`ToolChips` in `lib/claude.tsx` — **both** doors use it,
   `/claude` and `/gateway`. Adding a second renderer is exactly how the two
   drifted: for a month `/gateway` had role rails, markdown and tool chips while
   `/claude` — the view the whole product exists for — was flat `pre-wrap` text,
   because the good renderer was one import away and nobody imported it. A new
   view styles itself from the vocabulary or extends the vocabulary; it never
   grows a private one.
7. **The console opens on the MEMORY, not on the storage.** `/console` counts
   conversations, turns relayed and events, and lists what happened lately; the
   sidebar leads with the views and files the raw tables under `raw tables`. It
   used to open on `7 tables, 5,280 rows` — true, and the wrong first sentence.

## The security posture — read this before touching `lib/db.ts`

**A read-only transaction mode is not a read-only credential.** Learned by
breaking it: the first version of the read path relied only on transaction modes,
and `SET TRANSACTION READ WRITE` took the privilege straight back — a real
`'pwned'` row reached `aire_log` at `seq 2641`, and it is still there, because
append-only means the scar stays too.

So the wall is now **the credential**:

- The app connects as **`aire_reader`** (`GRANT SELECT`, nothing else) —
  `~/.secrets/aire-postgres-readonly.txt`. **Never** hand this repo
  `~/.secrets/aire-postgres.txt`: that is the daemon's pen.
- **`npm run attack` refuses to run** unless it arrived as a role that cannot
  INSERT. Point it at the pen and it stops dead — *"the waiter is holding the
  pen"* — instead of printing a comforting wall of "blocked". That guard exists so
  a stray env var cannot silently undo the fix.
- The four walls in `lib/db.ts` remain as **defence in depth**, not as the
  defence.
- The console is behind a **login page** with a signed session cookie
  (`app/login`, `lib/session.ts`, `middleware.ts`) and **fails closed**: no
  `AIRE_CONSOLE_PASSWORD` → `503`, serves nothing. Not HTTP Basic — the native
  prompt cannot be styled, cannot be logged out of, and breaks Chrome-DevTools
  verification (`ERR_INVALID_AUTH_CREDENTIALS`).

**The claim "this cannot write" is only ever backed by `npm run attack`.** Run it
after every change to the read path; do not reason about it.

## Performance is a correctness problem here, not a polish problem

The log grows **~2,500 rows/hour**. Anything that scales with its size is a bomb
with a date on it, and two of them shipped before they were caught:

- **The monster loaded the whole log into Node** (413 bytes of heap/row → 709 MB
  in a 1 GB container within 30 days). Counting now happens in Postgres and only
  ~50 aggregate rows cross the wire.
- **The obvious SQL rewrite was also a bomb**: one regex-with-lookahead per line
  costs 98 µs/row, which blows `statement_timeout` in 61 hours. It classifies on
  token position instead — 6.3 µs/row, proven identical against the live log.
- **`statement_timeout=15s` is load-bearing.** Wall 4 only checks a statement
  *begins* a read, so `SELECT pg_sleep(3600)` sails through it — and four of those
  exhaust `max: 4` and freeze the WHOLE app, since every page needs a connection
  for the sidebar.
- **`tables()` is wrapped in React `cache()`** because every page renders `<Shell>`.
  Without it, `/` ran two `count(*)` full scans per request.

**Measure before you believe a fix.** Both of the above looked correct and were
not; the numbers came from running them, not from reading them.

## Verified facts (don't re-discover them)

- **The database had ONE table on genesis day**: `aire_log` (`seq`, `at`,
  `line`), written by the droplet's listener, and the UI was built to DISCOVER
  tables rather than wait for them. That design paid off — as of 2026-08-22 there
  are **eight**: `aire_log`, `claude_session_store` (the agent's memory),
  `aire_gateway_log` + `aire_gateway_blob` (the relay's, deduped), `aire_casita`
  (each casita's persona), `aire_token`, `aire_device`, `aire_access_request`.
  Read the catalog, never a schema hardcoded here.
- **`pg` is more dangerous than `asyncpg` was.** With no parameters, node-postgres
  speaks the simple query protocol, which runs `SET …; DELETE …` as one
  transaction. Always pass `values` (even `[]`): that forces the extended protocol
  and one statement per round trip. `read()` in `lib/db.ts` does this.
- **The production build MINIFIES class names.** `err.constructor.name` renders as
  `n` in a built bundle — the SQL console shipped "n: This console only runs
  reads…" for one build. Use `err.name`, set explicitly on the class.
- **`sslmode=require` does not verify the certificate.** pg's legacy default
  accepts any cert, which is a MITM against a database on the public internet.
  `lib/db.ts` forces `rejectUnauthorized: true`; Azure's DigiCert chain is already
  in Node's trust store, so it costs nothing.
- **Someone on the internet already writes to the daemon's port.** The monster
  shows an `INTERNET-CAN-WRITE-HERE` node — port 9099 is open (see `aire-server`
  backlog #16). Not this repo's problem to fix, but don't be surprised by it.

## How to work here

- **English only**, like `aire-server`. Every byte committed is in English.
- **Verify against the real running state.** A `200` from `curl` is not a rendered
  page — open it in the browser and look.
- **`npm run attack` is not optional** on any change to the read path.
- **Bernard distinguishes learning from building.** When he is understanding
  something, don't rush ahead writing code: you would be stealing it from him.
- **Don't invert his architecture.** His stated direction is the most likely
  correct prior, especially in his own project. Stress-test it; never override it
  by force of insistence. Decision #2 above exists because that was violated once.
