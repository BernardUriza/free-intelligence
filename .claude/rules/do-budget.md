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
