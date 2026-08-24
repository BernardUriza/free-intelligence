# DigitalOcean budget — $20/month HARD, inventory is one droplet

Registered 2026-07-13 by Bernard's directive. AIRE's entire DigitalOcean budget
is **$20 USD/month**. Current run-rate: **$4/mo** (one `s-1vcpu-512mb-10gb`
droplet, no backups, no extras). This is an Art. 8 hard constraint, enforced —
not documentation.

## The budgeted inventory (exhaustive)

- Exactly **one** droplet: `aire-droplet`, size `s-1vcpu-512mb-10gb` (~$4/mo),
  region `nyc3`, **backups OFF**.
- **Nothing else.** Zero volumes, snapshots, reserved IPs, load balancers,
  managed databases, Kubernetes clusters, Spaces, registry.

## Prohibitions for every agent working this repo

1. **NEVER create, resize, or enable a paid DO resource without Bernard's
   explicit authorization in the current conversation** — that includes a
   second droplet, a bigger size, `--enable-backups`, snapshots, volumes,
   reserved IPs, and managed Postgres. This is the Art. 4 spend firewall made
   repo-specific. The documented size fallback (`SIZE=s-1vcpu-1gb`, ~$6/mo) is
   pre-authorized ONLY inside a provisioning run Bernard asked for.
2. **A destroyed-and-recreated droplet is a spend event too** — DO bills
   per-hour per droplet; churning droplets multiplies the line items. Reuse the
   existing one (the provision script is idempotent for this reason).
3. **When the budget question comes up, check the REAL spend, not the plan:**
   `doctl balance get` (month-to-date) and the inventory sweep
   (`droplets/volumes/snapshots/reserved-ips/load-balancers/databases`).

## Azure Postgres is the OTHER cloud — the pen writes there

The $20 cap governs DigitalOcean, where spend is frozen at $4. The component that
actually **grows** is the pen's `aire_log` table in **Azure Postgres**, fed by a
port open to the internet (accepted risk, see `server/deploy/aire-listener.service`). It
is capped by the **broom** (`server/aire/sweep.py` + `aire-sweep.timer`, 30-day
retention) and by **logrotate** on the file.

`costwatch` checks that nightly over SSH: a dead broom, a crashing sweep, or a
disk past 80% goes red. Since 2026-08-22 it also measures the thing itself —
`server/infra/growth.py` reports the database's size and every table's MB/day
over its own live window, red past `AIRE_DB_CEILING_MB`. Watching only the broom
was watching the wrong end: one that runs perfectly while the input rate climbs
is a green light over a rising line.

The **logrotate** half joined that nightly check on 2026-08-22, hours after
this paragraph was rewritten to admit it had not. It is four signals, because a config
that validates is not a rotation that happens: the config exists and parses,
`logrotate.timer` is active, the last rotation recorded in
`/var/lib/logrotate/status` is at most three days old (the one that cannot be
faked — `notifempty` buys the slack), and `aire.log` itself is under 64 MB.
Every one of them was proven able to go red on the droplet before it was
trusted, and the file's own record was put back afterwards.

**Never watch only the cloud where the spend is frozen.** The blind spot always
opens over the thing that grows.

## The external pulse — the only watcher that is not on the box

Everything else here runs ON the droplet or once a day from GitHub. Both blind
spots are the same one: a watchdog living on the box cannot report the box being
gone, and a daily cron finds a door that died at 14:00 at 13:17 the next day.

Since 2026-08-24 an **UptimeRobot free** account polls
`https://gate.bernarduriza.com/health` **every 5 minutes** from outside and mails
bernarduriza@gmail.com. It is a KEYWORD monitor — it opens an incident when
`"status":"ok"` is ABSENT — because a plain status check passes on any 200 and
Caddy can answer 200 with something that is not the app. $0: a 5-minute GitHub
cron on this private repo would be ~8,640 runs/month against 2,000 free minutes.

Credential and monitor ids: `~/.secrets/uptimerobot.txt`. It is the one alarm in
this file that costs nothing and sees the box from the outside; the others watch
what is inside it.

## Enforcement (the parts that alarm on their own)

- **`.github/workflows/costwatch.yml`** — daily cron: fails RED (→ GitHub
  emails Bernard) if month-to-date usage crosses **$10** (early warning) or
  **$20** (budget), if the droplet inventory drifts from the budgeted one, if
  any volume/snapshot/reserved-IP/LB/DB appears, or if backups get enabled.
  Reads the `DO_API_TOKEN` repo secret.
- **DO billing alert — SET at $10** (2026-07-13, control panel → Billing →
  Settings, team `382aae`): DO emails when the monthly balance reaches $10.00;
  independent of GitHub. Verified enabled on the rendered panel.
- DO has **no native hard cap** — nothing stops spend automatically; these
  alarms + prohibition 1 are the cap.

The $5 signup credit (expires Oct 2026) absorbs the first ~5 weeks; after that
the droplet bills the card on file.
