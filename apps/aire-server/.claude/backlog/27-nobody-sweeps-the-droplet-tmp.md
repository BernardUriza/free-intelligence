# Nobody sweeps the droplet's /tmp — resume temp dirs and stray artifacts pile up

Status: **Done 2026-07-20** (`f55cef4`) — verified live.
Proposed: 2026-07-20 by Claude (found auditing the parallel-books E2E)

## What shipped

`aire-tmpclean.timer` (hourly) runs `aire-tmpclean.service`, a oneshot
`find /tmp -maxdepth 1 -type d -name "claude-resume-*" -mmin +60 -exec rm -rf`.
The `-mmin +60` guard means a dir backing a live pooled client (younger than an
hour) is never touched. Installed by BOTH the deploy workflow and
`remote-bootstrap.sh`, so a kill test resurrects it (device-verb-protocol
durability). Verified live: timer `active`, next run scheduled, the exact find
removed a 3h-old dir and left a fresh one, the service exits 0.

**The tmpfiles.d route was tried first and rejected by evidence** (Loop Law): a
dry-run on the droplet showed the `e` type only cleans dir CONTENTS, never
age-removes whole dirs matching a glob — both test dirs survived. The find timer
is the AIRE-native pattern anyway (aire-sweep/mirror), so Art. 6 favoured it.

The stray-artifact half (a book in /tmp) is moot since #24 (the cage): agents can
no longer write outside their casita, so nothing lands in /tmp to sweep.

## What it is

The broom ([[do-budget]], `sweep.py`) prunes `aire_log` in Postgres, and
logrotate rotates `aire.log`. **Nothing prunes the droplet's `/tmp`.** After a
few hours of testing it holds:

- **7 `/tmp/claude-resume-*` dirs**, up to 1.4M each — the SDK materializes the
  store into a temp dir (`CLAUDE_CONFIG_DIR=/tmp`, decision #4) on every resume
  and does not clean them up. One accrues per resume, forever.
- **`/tmp/ajedrez/`** — a whole book an agent wrote outside its casita (see #24).

Disk is at 42% of 8.7G today, so this is not urgent — but it is monotonic growth
on a mortal 10G disk that never reboots, and it is exactly the "watch the thing
that GROWS" blind spot [[do-budget]] already names for Azure Postgres. The pen's
growth is capped by the broom; the droplet's `/tmp` growth is capped by nothing.

## Canonical path to reuse (Art. 6)

`systemd-tmpfiles` is the canonical Linux answer — a `/etc/tmpfiles.d/aire.conf`
line aging out `/tmp/claude-resume-*` older than, say, 1 hour. It is infra, not
app code, so it belongs in `provision-do.sh` + `infra/` (persisted like every
other config per [[device-verb-protocol]]'s durability model), never a manual
`rm`. This also keeps it in the Linux-curriculum spirit — a real tmpfiles rule
on a real box.

Do NOT blind-`rm /tmp/claude-resume-*` while the daemon is live: a dir may back a
client currently in the pool. Age-based cleanup (tmpfiles) avoids that; a manual
sweep does not.

## The decision that's the owner's

It is a provisioning change on the live box — low blast radius, but infra that
Bernard owns and that is also his Linux classroom. His call whether to add the
tmpfiles rule now or let it ride until disk pressure is real. The artifact-in-
/tmp half is downstream of #24 (the cage): fix the cage and stray books stop
landing in /tmp in the first place.

## Status / next step

Not built. One tmpfiles.d line + a provision-script entry once Bernard okays the
infra touch. Independent of #24 but complementary.
