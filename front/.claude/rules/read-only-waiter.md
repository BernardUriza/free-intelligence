# This repo only reads — the pen lives in `aire-server`

Repo rule for `aire-front-seed`. It is the mirror image of `aire-server`'s
`write-only-daemon` law, and together they are one law with two halves: the
daemon appends and never reads; the front reads and never appends. The
append-only table is the frontier between them.

## The law

1. **No write reaches Postgres from this repo.** No `INSERT`, `UPDATE`, `DELETE`,
   no DDL, no `COPY`, not for a migration, not for a "quick fix", not for a
   cache table. If a write seems necessary, the feature belongs in `aire-server`
   or it does not exist.
2. **`lib/db.ts` is the only module that opens a connection.** A page, a route or
   a component that imports `pg` directly is a violation. One door, so the walls
   are in one place.
3. **The daemon owns the DDL.** This repo treats the schema as a read-only
   contract discovered from the catalog at runtime — never a hardcoded model, and
   never a migration. A schema change is an API change between the two repos.
4. **Every claim that "it cannot write" is proven by `npm run attack`, not by
   reading the code.** See below: the code lied once already.

## The wall that cannot be argued with: the credential

**`aire_reader` — `GRANT SELECT`, and nothing else.** The app arrives as a role
that does not *have* the `INSERT` privilege, so there is nothing for an attacker
to re-enable. `npm run attack` refuses to run at all unless it connected as such a
role, and says so:

```
connected as 'aire_reader' — reads aire_log, CANNOT insert into it.
the credential itself is the wall; what follows is defence in depth.
```

Point `AIRE_DATABASE_URL` at the pen's credential and the suite does not print a
comforting wall of "blocked" — it stops dead: *"the waiter is holding the pen."*
That check exists so this fix cannot be silently reverted by a stray env var.

Credential: `~/.secrets/aire-postgres-readonly.txt`. **Never** give this repo
`~/.secrets/aire-postgres.txt` — that is the daemon's pen.

Tables the daemon creates *later* are covered without anyone remembering to act:

```sql
ALTER DEFAULT PRIVILEGES FOR ROLE aire IN SCHEMA public GRANT SELECT ON TABLES TO aire_reader;
```

## The four walls behind it, and why they are still there

**A read-only *transaction mode* is not a read-only *credential*.** That is the
whole lesson, and it was learned by breaking it:

On 2026-07-13 the first version of the read path set
`default_transaction_read_only=on` on the connection and declared the console
safe. It was not. That setting is a **default**, and the `aire` role — the pen's
own credential — **owned write privileges**. A plain `SET TRANSACTION READ WRITE`
took them straight back, the `INSERT` after it went through, and a row of garbage
(`'pwned'`) landed in the production log at `seq 2641`. It is still there: the log
is append-only, and to correct is to append, not to erase.

The credential fix above makes that attack impossible. The four walls below stay
anyway — defence in depth, and the thing that keeps a future local run (pointed at
some other database by a tired hand) from doing damage:

| # | Wall | Stops |
|---|------|-------|
| 1 | `default_transaction_read_only=on` on the connection | a casual write |
| 2 | explicit `BEGIN … READ ONLY` per statement | a write on a poisoned pooled connection |
| 3 | extended query protocol (always pass `values`) | `SET TRANSACTION READ WRITE; DELETE …` in one round trip |
| 4 | the statement must BEGIN a read (`READS_ONLY`) | the `SET` that would disarm walls 1 and 2 |

Wall 3 exists because **node-postgres is more dangerous than the Python driver
was**: `pg` speaks the simple query protocol when a query has no parameters, and
the simple protocol runs multiple statements in one transaction. What `asyncpg`
refused for free, `pg` hands to an attacker.

Wall 4 was the load-bearing one *while the credential could write*. It no longer
carries the building — but it still catches the tired hand.

**Proof the credential is the real wall, not the walls:** with every wall bypassed
(raw `psql`, no app, no transaction mode), `aire_reader` still cannot write —
including via the exact attack that defeated the walls:

```
$ psql "$AIRE_READER_DSN"
aire=> SELECT count(*) FROM aire_log;        -- 6137
aire=> BEGIN; SET TRANSACTION READ WRITE;
aire=> INSERT INTO aire_log (line) VALUES ('pwned-again');
ERROR:  permission denied for table aire_log
aire=> DROP TABLE aire_log;
ERROR:  must be owner of table aire_log
aire=> CREATE TABLE evil (a int);
ERROR:  permission denied for schema public
```

## The door

A **login page** (`app/login/page.tsx`) and a **signed session cookie**
(`lib/session.ts`) — server-rendered HTML and a Server Action, no client
JavaScript, like every other page here.

It was HTTP Basic for exactly one deploy. The browser's native prompt cannot be
styled, cannot be **logged out of**, is hostile on a phone, and broke automated
navigation outright (`ERR_INVALID_AUTH_CREDENTIALS` — it defeated this repo's own
Chrome-DevTools verification). A login is a page, like everything else.

- **The cookie is signed, not stored.** HMAC-SHA-256 over its own expiry, keyed
  with the console password. No session table, no state in the container (the
  daemon's law, kept here too), and a restart logs nobody out. **Change the
  password and every outstanding cookie dies** — which is what changing a password
  should mean.
- `httpOnly` (a stray XSS cannot read it), `secure` in production, `sameSite=lax`.
- **Fails closed**: with `AIRE_CONSOLE_PASSWORD` unset the app answers `503` and
  serves nothing. An unset variable must never be why a database ends up public.
- **The `?next=` redirect is validated.** `//evil.com`, `/\evil.com` and
  `https://evil.com` all collapse to `/`. An open redirect turns a login page into
  a phishing tool: the URL people are told to trust is the one that sends them
  elsewhere.
- Sign-out is a **POST**, never a link — a GET that changes state can be fired by
  any `<img>` on any page.

It guards the **app**, not the deployment — it holds identically under `docker
run`, `next start` and Container Apps. A console that is private only because the
infrastructure happens to be configured right is one `az` flag away from public.

`/api/health` is the single unauthenticated route (a liveness probe cannot carry a
credential), so it is also the one route that gives nothing away: it reports that
it can read, never *what*. It used to answer with the table names and their row
counts — that is the schema, published to anyone who asked.

Password: `~/.secrets/aire-console-password.txt`.

## How to apply

- Touching `lib/db.ts`? Run `npm run attack` before you believe anything.
- Adding a page? It reads through `lib/db.ts`, or it does not read.
- Adding a route that must skip auth? Almost certainly no. If truly yes, it may
  not disclose the schema, the data, or the existence of either.
- Tempted to cache a derived table in Postgres? That is a write. Derive it at
  render time, or ask `aire-server` to own it.
