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

**A read-only transaction mode is not a read-only credential.** This app connects
with `aire`, the *pen's own* credential, which owns write privileges. Four walls
keep it from using them, and the fourth is load-bearing: it blocks the
`SET TRANSACTION READ WRITE` that dissolves the other three.

The walls, and the story of how the first version was breached (a real `'pwned'`
row landed in `aire_log` at `seq 2641`), are in the rule. **The claim "this cannot
write" is only ever backed by `npm run attack`** — 13 write attempts against the
real database, all of which must be refused. Run it after every change to the read
path; do not reason about it.

The real fix — an `aire_reader` role with `GRANT SELECT` and nothing else — is
backlog #1 and needs the Postgres server admin.

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
