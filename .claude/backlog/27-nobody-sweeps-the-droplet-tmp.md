# Nobody sweeps the droplet's /tmp — resume temp dirs and stray artifacts pile up

Status: Proposed
Proposed: 2026-07-20 by Claude (found auditing the parallel-books E2E)

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
