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

## The two secrets

**To just get in, read the [Get in](../README.md#get-in) section of the README** —
it has the one-liner and what to do when the door won't open. This file is for the
deployment; that one is for the door.

The ingress is public, and that is fine, because the console is not.

| Secret | Holds | Source |
|---|---|---|
| `aire-database-url` | `aire_reader` — `GRANT SELECT`, nothing else | `~/.secrets/aire-postgres-readonly.txt` |
| `aire-console-password` | the HTTP Basic password on every page | `~/.secrets/aire-console-password.txt` |

**Never put `~/.secrets/aire-postgres.txt` here.** That is the daemon's pen — a
write-capable credential — and `npm run attack` will refuse to run if it ever finds
itself holding it.

The app **fails closed**: without `AIRE_CONSOLE_PASSWORD` it answers `503` and
serves nothing. A missing variable must never be why a database ends up public.
`/api/health` is the one route that skips auth (a probe cannot carry a credential),
and it discloses nothing but its own liveness.

## Build the image

The canonical path is `az acr build` **on the GitHub runner** (`az` on this Mac has
a broken `pyexpat` and fails the source-upload step — see `~/CLAUDE.md`). Push to
`main` and let CD build it. To build by hand from a machine with a working `az`:

```bash
az acr build -r insultacr -t aire-front:$(git rev-parse --short HEAD) -t aire-front:latest .
```

## Create the app (once)

```bash
DSN=$(grep '^AIRE_DATABASE_URL=' ~/.secrets/aire-postgres-readonly.txt | cut -d= -f2-)
PW=$(grep '^AIRE_CONSOLE_PASSWORD=' ~/.secrets/aire-console-password.txt | cut -d= -f2-)

az containerapp create \
  -n aire-front -g insult-rg \
  --environment prod-env \
  --image insultacr.azurecr.io/aire-front:latest \
  --registry-server insultacr.azurecr.io \
  --secrets "aire-database-url=$DSN" "aire-console-password=$PW" \
  --env-vars "AIRE_DATABASE_URL=secretref:aire-database-url" \
             "AIRE_CONSOLE_PASSWORD=secretref:aire-console-password" \
  --target-port 3000 \
  --ingress external \
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
