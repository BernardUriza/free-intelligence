# Infra — the waiter on Azure Container Apps

**LIVE:** https://aire-front.greendune-53f1f4af.eastus2.azurecontainerapps.io
(deployed 2026-07-13, `--ingress external`, scales to zero)

Nothing new was provisioned. The registry, the environment and the resource group
already existed and already hold the database this app reads — reusing them is
both cheaper and faster (same region, so the Postgres round trip never leaves
East US 2).

| Thing | Value | Why this one |
|---|---|---|
| Resource group | `insult-rg` | already holds `development-pg-n66dz`, AIRE's Postgres |
| Registry | `insultacr.azurecr.io` | already builds images for `discord-bot` |
| Environment | `prod-env` (East US 2) | same region as the database |
| App name | `aire-front` | — |
| Secret | `aire-database-url` | injected at runtime, never in an image layer |

## The console is PUBLIC and has NO authentication

Stated plainly rather than buried: **anyone who finds that URL can read the entire
database** — every line the daemon has ever appended, and every table it creates
from now on. It cannot *write* (see
[`../.claude/rules/read-only-waiter.md`](../.claude/rules/read-only-waiter.md)),
but reading is precisely what a console is for.

This was a deliberate call by Bernard on 2026-07-13 ("external — lo quiero ver
ya") on a database that today holds one table of simulated GPS heartbeats. **It
stops being an acceptable trade the moment `claude_session_store` appears**: that
table is the transcript of real agent conversations, and an unauthenticated
`/sql` console over it is a data leak with a URL.

**Auth is backlog #5, and it is a blocker for the engine phase, not a nice-to-have.**
Until it lands, either keep the database boring or flip the ingress:

```bash
az containerapp ingress enable -n aire-front -g insult-rg \
  --type internal --target-port 3000 --transport auto
```

## Build the image

The canonical path is `az acr build` **on the GitHub runner** (`az` on this Mac has
a broken `pyexpat` and fails the source-upload step — see `~/CLAUDE.md`). Push to
`main` and let CD build it. To build by hand from a machine with a working `az`:

```bash
az acr build -r insultacr -t aire-front:$(git rev-parse --short HEAD) -t aire-front:latest .
```

## Create the app (once)

```bash
DSN=$(grep '^AIRE_DATABASE_URL=' ~/.secrets/aire-postgres.txt | cut -d= -f2-)

az containerapp create \
  -n aire-front -g insult-rg \
  --environment prod-env \
  --image insultacr.azurecr.io/aire-front:latest \
  --registry-server insultacr.azurecr.io \
  --secrets "aire-database-url=$DSN" \
  --env-vars "AIRE_DATABASE_URL=secretref:aire-database-url" \
  --target-port 3000 \
  --ingress internal \
  --min-replicas 0 --max-replicas 2 \
  --cpu 0.5 --memory 1Gi
```

`--min-replicas 0` lets it scale to zero: the console costs nothing while nobody
is looking at it, which is the right shape for a thing you open a few times a day.
The cold start is a couple of seconds — the standalone server carries no
`npm install` and no build.

## Update it (every deploy)

```bash
az containerapp update -n aire-front -g insult-rg \
  --image insultacr.azurecr.io/aire-front:<sha>
```

## Verify it — the real surface, not a proxy

```bash
FQDN=$(az containerapp show -n aire-front -g insult-rg --query properties.configuration.ingress.fqdn -o tsv)
curl -s "https://$FQDN/api/health"    # {"status":"ok","access":"read-only",...}
```

A `200` from `/api/health` proves the process is up and can reach Postgres. It
does **not** prove the pages render — open `/`, `/t/aire_log` and `/monster` in a
browser and look at them. (`aire-server`'s law: observe the real running state.)

## Rotating the DSN

```bash
az containerapp secret set -n aire-front -g insult-rg --secrets "aire-database-url=$NEW_DSN"
az containerapp revision restart -n aire-front -g insult-rg \
  --revision $(az containerapp show -n aire-front -g insult-rg --query properties.latestRevisionName -o tsv)
```

The secret lives in Container Apps and in `~/.secrets/` — never in this repo, never
in an image layer, never in a workflow literal.
