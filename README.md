# AIRE front

**The waiter** — a phpMyAdmin for the database [AIRE](../aire-server) writes.
Read-only, server-rendered, live on Azure Container Apps:

**https://aire-front.greendune-53f1f4af.eastus2.azurecontainerapps.io**

> EC-GPS had a Perl daemon that only wrote and a PHP console that only read, and
> it printed money for two decades. `aire-server` is the daemon. This is the
> console.

> ⚠️ **That URL is public and has no authentication.** Anyone who finds it reads
> the whole database. It cannot write — but the day `claude_session_store` lands,
> an open console over real transcripts is a leak with a URL. Auth is
> [backlog #5](.claude/backlog/README.md) and it blocks the engine phase.

## What it does

| Page | What it is |
|---|---|
| `/` | Every table the daemon has created, with row counts and size |
| `/t/{table}` | Browse it: paginated, sortable, searchable across every text column |
| `/sql` | A SQL console. Type `DELETE FROM aire_log` and watch the database refuse |
| `/monster` | The directly-follows graph of `aire_log` — process mining over the event log |
| `/api/health` | `{"status":"ok","access":"read-only",…}` — what Container Apps probes |

**The schema is discovered, never hardcoded.** The table list comes from the live
Postgres catalog, so when the daemon creates `claude_session_store` tomorrow it
appears in the sidebar with no code change here.

## It cannot write — and that is tested, not asserted

This repo reads a database it does not own. The transcript is **append-only**
(`aire-server`'s law), so the front is forbidden from writing — and the
prohibition is enforced four times over, because the first version of it was
defeated in about a minute and a row of garbage landed in production.

```bash
npm run attack
#   blocked  plain DELETE             NotARead
#   blocked  disarm the transaction   NotARead
#   blocked  disarm, then write       NotARead
#   blocked  data-modifying CTE       error
#   … PASSED — 13 write attempts, all refused, aire_log untouched.
```

The four walls, and the story of how the first one fell:
[`.claude/rules/read-only-waiter.md`](.claude/rules/read-only-waiter.md).

**Known weakness, written down rather than hidden:** the app still connects with
the pen's own credential (`aire`, which *can* write). The real fix is a role that
`GRANT SELECT`s and nothing else — it needs the Postgres server admin. See the
[backlog](.claude/backlog/README.md).

## Run it

```bash
export AIRE_DATABASE_URL='postgresql://…'   # the pen's DSN; the reader only SELECTs
npm install
npm run dev            # http://localhost:3000
npm run attack         # prove it cannot write
```

## Ship it

Next.js SSR in a container — every route is `force-dynamic`, nothing is
prerendered, and the database is a **runtime** dependency (no DSN is ever baked
into an image layer).

```bash
docker build -t aire-front .
docker run -p 3000:3000 -e AIRE_DATABASE_URL='…' aire-front
```

Azure Container Apps runbook — the app, the secret, the ingress:
[`infra/README.md`](infra/README.md).

## Architecture

```
  aire-server  ──writes──►  Postgres  ◄──reads──  aire-front  (you are here)
   the pen                 append-only             the waiter
   (the daemon)             the truth              (the console)
```

Two repos, two deployments, one append-only table as the frontier. CQRS at repo
granularity — the EC-GPS blueprint exactly. The daemon's half of the law:
[`aire-server/.claude/rules/write-only-daemon.md`](../aire-server/.claude/rules/write-only-daemon.md).

## Stack

Next.js 16 (App Router, Server Components) · React 19 · `pg` · plain CSS.
No client JavaScript ships for any page: the SVG, the tables and the forms are
all server-rendered HTML.
