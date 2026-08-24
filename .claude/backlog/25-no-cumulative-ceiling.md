# No cumulative spend ceiling is actually set

Status: **Ledger shipped 2026-08-23; the ceiling stays per-process on purpose.**
Bernard set **$20** on 2026-08-20 (`~/.secrets/aire-budget.txt` + `append_secret`,
`ec58e0d`) and it armed a counter born at `0.0` on every start — the daemon
restarts on every deploy, fourteen times on 2026-08-23 alone, so a ceiling
called cumulative was counting from zero several times a day while
`arming.py` reported `spend_backstop: armed`. `aire/spend.py` now appends a row
per paid turn to `aire_spend` (both doors), `/health`'s gated half reports
`spend_month_usd`, and costwatch goes red when the month crosses $20. Asked
whether the month should also REFUSE, Bernard chose alarm-only: a hard monthly
cap can take og118 and Fénix down at 3am over an accounting threshold, and the
per-process backstop already stops a single runaway session.

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


## What shipped, 2026-08-23 — and what deliberately did not

`aire/spend.py`, appended to by both doors at the seams that already knew the
dollars: the engine's result seam (`engine/turn.py::_account`, banking the
DELTA the ledger banks, never `total_cost_usd`, which is the client's
cumulative spend) and the gateway's biller (`tokens.biller`, where a lent or
metered turn is already priced). A pass-through turn costs AIRE nothing and
writes no row.

Three things this fixes that were not in the original item:

- **The daemon could not answer "what did I spend this month."** `aire_token`
  held per-invitation totals and `aire_gateway_log` held raw `usage`; nowhere
  did a dollar survive in a form anyone could sum. The month was unanswerable,
  not merely uncapped.
- **`arming.py` reported the guard armed**, which was true of the env var and
  false of the protection. It says so now, and points at the figure that is
  real.
- **The watchdog watched the wrong cloud again.** [[do-budget]]'s own law —
  *never watch only the cloud where the spend is frozen* — had been applied to
  the database's growth and never to the Anthropic bill behind the same door.

**Not shipped, by decision:** the monthly refusal. `AIRE_MAX_SPEND_USD` keeps
its per-process meaning. If the alarm ever fires on a month nobody can explain,
that is the moment to revisit — not before.

**Known limit:** the first month is partial. The table starts on 2026-08-23, so
August's figure counts only from that day, and the first honest full month is
September.

## The defect the review found in the ledger it was built on (same day)

`/cruel-critic`, hours after the above shipped: the RAM ledger banks a DELTA
against the client's CUMULATIVE `total_cost_usd`, and **only `_retire` (#23)
ever cleared its memory of a client.** Eviction does not go through `_retire` —
`pool.evict()` and `make_space()` call `close_one` directly, and on a two-slot
pool with a casita per chat that is the COMMON path. So a reborn client, whose
own cumulative starts at zero, met a remembered predecessor and `max(0.0, cost
- seen)` clamped its turns to **$0** until it out-spent the dead one.

Measured, not reasoned: a client banking 0.028 → 0.030 → 0.033, then a reborn
one at 0.025, banked **$0.00** for a paid turn — no ceiling movement and **no
`aire_spend` row at all**. The very table shipped that morning to make the month
trustworthy was being fed by a counter that silently skipped turns.

Fixed at the client's BIRTH (`Ledger.adopt`, called by `_client_for`), which is
the only moment the `_seen` invariant becomes true again regardless of which
exit the previous client took. `_drop`'s docstring, which claimed to be "the ONE
way a client leaves the pool", was corrected — that false invariant is what made
the bug invisible to a careful reader. Two regression tests, both proven red
against the unfixed code before being trusted.
