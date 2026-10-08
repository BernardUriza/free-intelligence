# Scheduled backups of the memory

Status: **Done — covered by the platform** (verified 2026-07-20). No code needed.
Proposed: 2026-06 (original backlog)

## What it is

The database is AIRE's one irreplaceable piece (`README`: *"delete the database
and AIRE is dead"*). The original item proposed a `pg_dump` + cron to back it up.

## The 2026-07-20 check — Azure already backs it up

Before building anything (Art. 6/7 — don't reinvent what the platform gives),
`az postgres flexible-server show` on `development-pg-n66dz` (rg `insult-rg`):

```
backupRetentionDays : 7
earliestRestore     : 2026-07-14T21:55Z   (point-in-time restore, ~7 days)
geoRedundant        : Disabled
tier                : Burstable, PG 16, 32 GB
```

So the main risk — an accidental `DELETE`/`DROP`, corruption, a bad migration —
is already covered: Azure Flexible Server takes automatic backups and supports
point-in-time restore to any moment in the last 7 days. A hand-rolled
`pg_dump` + cron would duplicate this (Art. 6, reinvention is the smell) and add
a mortal artifact to maintain. **Dropped as redundant.**

## The one gap, and why it stays Bernard's (and probably a no)

`geoRedundant: Disabled` — the backups live in the same region (`eastus2`) as the
server, so a total regional loss of Azure would take the backups with it. Enabling
geo-redundancy costs money and is an Art. 8 spend decision. Stress-tested (Art. 7):
for a Burstable DB holding books and a log, on the $20/mo posture, a whole-region
Azure outage is a remote enough worst case that geo-redundancy is over-engineering.
Noted, not pitched — Bernard's call if he ever wants it.

## Status / next step

Nothing to build. The memory is backed up (7-day PITR). The `~/.secrets/` note and
the README status were corrected to say so, so no future agent re-proposes a
pg_dump the platform already renders.
