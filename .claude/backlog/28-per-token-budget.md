# Per-token budget — the canary key is revocable but not independently capped

Status: **Proposed** 2026-07-27 by Claude (found lighting up the Azure canary door)
Proposed: 2026-07-27

## What it is

The LLM door now accepts two Bearer tokens (`AIRE_AUTH_TOKEN` — Bernard's own —
and `AIRE_CANARY_TOKEN` — the lower-trust key handed to the Azure front). A leak
of the canary is **revocable** (drop the env var, restart) without rotating
Bernard's key. But the spend cap `AIRE_MAX_BUDGET_USD` is **global to the
daemon**, not per-token: a leaked canary, until noticed and revoked, can burn the
WHOLE budget, starving Bernard's own turns.

The wanted shape: each accepted token carries its own ceiling (e.g. the canary
gets $2/day, Bernard's is uncapped), so a canary abuse can never exhaust the
primary's headroom.

## Canonical path to reuse (Art. 6)

The accounting already exists — `engine/core.py` `_account()` banks the per-turn
delta into `self._spend_usd` against `AIRE_MAX_BUDGET_USD`. Extend it to a dict
keyed by the presented token (or a token *label*), each with its own ceiling,
instead of one scalar. The middleware in `server.py` already knows which token
matched — pass that identity down so the turn is billed to the right bucket.

## The decision that's the owner's

The ceiling numbers and whether the primary is truly uncapped are Bernard's spend
call — same family as #23/#25 (the budget-cap items). Don't invent the dollar
figures.

## Status / next step

Not built. Today the canary's blast radius is bounded only by the GLOBAL cap and
by how fast a leak is noticed and revoked — documented honestly in
`~/.secrets/aire-canary-token.txt`. Related: [[23-the-budget-cap-lies-twice]],
[[25-no-cumulative-ceiling]].
