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
- The console is behind **HTTP Basic** (`middleware.ts`) and **fails closed**: no
  `AIRE_CONSOLE_PASSWORD` → `503`, serves nothing.

**The claim "this cannot write" is only ever backed by `npm run attack`.** Run it
after every change to the read path; do not reason about it.

## Verified facts (don't re-discover them)

- **The database has ONE table today**: `aire_log` (`seq`, `at`, `line`), written
  by the droplet's listener. `claude_session_store` does not exist yet — the
  engine has never run against this database. The UI is built to discover it, not
  to wait for it.
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
