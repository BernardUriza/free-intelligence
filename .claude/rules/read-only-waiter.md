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

## The walls, and why there are four

A read-only *transaction mode* is not a read-only *credential*. This is the whole
lesson, and it was learned by breaking it:

On 2026-07-13 the first version of the read path set
`default_transaction_read_only=on` on the connection and declared the console
safe. It was not. That setting is a **default**, and the `aire` role — the pen's
own credential — **owns write privileges**. A plain `SET TRANSACTION READ WRITE`
took them straight back, the `INSERT` after it went through, and a row of garbage
(`'pwned'`) landed in the production log at `seq 2641`. The wall was real; the
credential walked around it.

So the console now stands behind four:

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

Wall 4 is the load-bearing one *while the credential can write*. Remove it and
walls 1–2 can be switched off by the very SQL they contain.

## The real fix (not yet done)

**A credential that cannot write:** role `aire_reader`, `GRANT SELECT` on the
schema, nothing else. Then `SET TRANSACTION READ WRITE` buys an attacker
precisely nothing, and the four walls become the belt behind the braces rather
than the only thing holding the trousers up.

It needs the Postgres server admin (`devadmin` on `development-pg-n66dz`), which
the `aire` role does not have (`rolcreaterole = false`, verified). Until then, the
front runs with the pen's own credential, and **that is a known, written-down
weakness, not a solved problem.**

```sql
-- run as the server admin, once
CREATE ROLE aire_reader LOGIN PASSWORD '<generated>';
GRANT CONNECT ON DATABASE aire TO aire_reader;
GRANT USAGE ON SCHEMA public TO aire_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO aire_reader;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO aire_reader;
```

The day that lands, `npm run attack` must **still pass with the four walls
deleted**. That is the test that the real fix is real.

## How to apply

- Touching `lib/db.ts`? Run `npm run attack` before you believe anything.
- Adding a page? It reads through `lib/db.ts`, or it does not read.
- Tempted to cache a derived table in Postgres? That is a write. Derive it at
  render time, or ask `aire-server` to own it.
