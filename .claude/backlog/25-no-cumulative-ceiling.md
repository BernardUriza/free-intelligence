# No cumulative spend ceiling is actually set

Status: Proposed
Proposed: 2026-07-20 by Claude (found while auditing the budget defect, #23)

## What it is

The engine has TWO ceilings and only one of them is armed on the droplet.

- `AIRE_MAX_BUDGET_USD` (→ the SDK's `max_budget_usd`) — **set to `1.0`**. Caps a
  single client, and #23 now makes a cut turn say so.
- `AIRE_MAX_SPEND_USD` — the engine's own cumulative backstop over the process
  lifetime, which refuses turns BEFORE they reach the API with a real
  `BudgetExceeded`. **Absent from `/etc/aire/env`**, so `MAX_SPEND_USD is None`
  and the guard never fires.

Net effect: nothing caps what the daemon spends in total. Each new session gets
a fresh $1.00 allowance, and sessions are free to create (`_cwd` does
`mkdir(exist_ok=True)` on any project name — no `MKDIR` verb required). Today's
session spent **$4.84** across a handful of turns without ever approaching a
ceiling, because the only ceiling is per-client.

This is the same blind spot [[do-budget]] already names in another cloud: *"never
watch only the cloud where the spend is frozen."* DigitalOcean is frozen at $4/mo
and alarmed; the Anthropic spend behind this port is neither.

## Canonical path to reuse (Art. 6)

Nothing to build — the guard EXISTS in `engine/core.py` and raises
`BudgetExceeded`, which `server.py` already maps to an in-stream `error` event.
It only needs its env var set, and per [[device-verb-protocol]]'s persistence
model, set in the place a re-provision restores: `~/.secrets/` + a line in
`provision-do.sh`, never hand-edited into `/etc/aire/env`.

One caveat worth naming: the counter is per-process and **resets on restart**, so
it is a runaway backstop, not an accounting ledger. A daily restart silently
refills it.

## The decision that's the owner's

**The number, and whether a process-lifetime counter is even the right shape.**
It is spend, so it is Bernard's ([[do-budget]] Art. 8). A ledger that survives
restarts would have to live in Postgres — which is a READ from this repo, so it
would need his blessing as a third sanctioned exception to
[[write-only-daemon]], or it belongs in the front as a view over usage the pen
already writes.

## Status / next step

Not built. One line of config once Bernard picks the number; the ledger question
is a separate, larger call.
