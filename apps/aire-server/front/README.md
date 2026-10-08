# AIRE front

**The waiter** — a phpMyAdmin for the database [AIRE](../aire-server) writes.
Read-only, server-rendered, live on Azure Container Apps:

**https://aire.bernarduriza.com**

> EC-GPS had a Perl daemon that only wrote and a PHP console that only read, and
> it printed money for two decades. `aire-server` is the daemon. This is the
> console.

Behind a login page, connecting as a Postgres role that **holds `GRANT SELECT`
and nothing else**.

## Get in

The password is **not in this repo and never will be** — it lives in
`~/.secrets/`. One line puts it on the clipboard and opens the door:

```bash
grep '^AIRE_CONSOLE_PASSWORD=' ~/.secrets/aire-console-password.txt | cut -d= -f2- | tr -d '\n' | pbcopy
open https://aire.bernarduriza.com
```

Paste, Enter. The session lasts a week; **sign out** is at the bottom of the
sidebar.

Any URL you were trying to reach survives the login — `/monster` sends you to
`/login?next=/monster` and lands you back on `/monster` afterwards.

<details>
<summary>When it doesn't let you in</summary>

| What you see | What it means | What to do |
|---|---|---|
| **`503` — "refuses to serve without a door"** | `AIRE_CONSOLE_PASSWORD` is unset on the container. The app **fails closed on purpose**: a missing variable must never be why a database ends up public. | Set the secret (below) and restart the revision. |
| **"Wrong password"** | The password on the container and the one in `~/.secrets/` have drifted. | Re-set both from the same value (below). |
| **The page loads but says "The database is unreachable"** | The door is fine; the database is not. The console never writes, so this is never *its* fault — check the daemon's Postgres. | `curl .../api/health` → `degraded` confirms it. |
| **You are logged out for no reason** | The password was rotated. **That is the design:** the session cookie is signed *with* the password, so changing it kills every outstanding cookie. | Log in again with the new one. |

**Rotate the password** (kills every live session, which is the point):

```bash
NEW=$(openssl rand -base64 24 | tr -dc 'A-Za-z0-9' | head -c 28)
sed -i '' "s|^AIRE_CONSOLE_PASSWORD=.*|AIRE_CONSOLE_PASSWORD=$NEW|" ~/.secrets/aire-console-password.txt
az containerapp secret set -n aire-front -g insult-rg --secrets "aire-console-password=$NEW"
az containerapp revision restart -n aire-front -g insult-rg \
  --revision $(az containerapp show -n aire-front -g insult-rg --query properties.latestRevisionName -o tsv)
```

The secret lives in Container Apps and in `~/.secrets/`. **Never in this repo,
never in an image layer, never in a workflow literal.**
</details>

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
(`aire-server`'s law), so the front is forbidden from writing.

The wall is **the credential**: the app connects as `aire_reader`, a Postgres role
holding `GRANT SELECT` and nothing else. There is no privilege for an attacker to
re-enable. Four more walls sit behind it in `lib/db.ts` as defence in depth —
because the *first* version of this had only those walls, and they fell in about a
minute (`SET TRANSACTION READ WRITE` took the privilege straight back, and a row of
garbage reached production; it is still in `aire_log` at `seq 2641`, because
append-only means the scar stays too).

```bash
npm run attack
# connected as 'aire_reader' — reads aire_log, CANNOT insert into it.
# the credential itself is the wall; what follows is defence in depth.
#   blocked  disarm the transaction   NotARead
#   blocked  data-modifying CTE       error
#   … PASSED — 13 write attempts, all refused, aire_log untouched.
```

Hand it the pen's credential by mistake and it does not print a comforting wall of
"blocked" — it stops dead: *"the waiter is holding the pen."* The whole story:
[`.claude/rules/read-only-waiter.md`](.claude/rules/read-only-waiter.md).

## Run it

```bash
export AIRE_DATABASE_URL=$(grep '^AIRE_DATABASE_URL=' ~/.secrets/aire-postgres-readonly.txt | cut -d= -f2-)
export AIRE_CONSOLE_PASSWORD=$(grep '^AIRE_CONSOLE_PASSWORD=' ~/.secrets/aire-console-password.txt | cut -d= -f2-)
npm install
npm run dev            # http://localhost:3000 — it will ask for the password
npm run attack         # prove it cannot write
```

Without `AIRE_CONSOLE_PASSWORD` the app **refuses to serve** (503). It fails
closed: an unset variable must never be why a database ends up public.

## Ship it

Next.js SSR in a container — every route is `force-dynamic`, nothing is
prerendered, and the database is a **runtime** dependency (no DSN is ever baked
into an image layer).

```bash
docker build -t aire-front .
docker run -p 3000:3000 \
  -e AIRE_DATABASE_URL='postgresql://aire_reader:…' \
  -e AIRE_CONSOLE_PASSWORD='…' \
  aire-front
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
