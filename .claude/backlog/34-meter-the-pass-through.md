# Meter the pass-through — the caller with their own credential is invisible to the till

Status: **Proposed** 2026-08-15 by Bernard
Proposed: 2026-08-15

## What it is

This is **AIRE's slice of a product decision that lives elsewhere**: Bernard wants an
income source of his own that takes him out of the 1099/W2 cycle and into owning a
business with revenue. The product is a turn-key Discord server — a client's own server,
with bots whose persona Alex Nava designs, delivered with a capped, revocable AIRE key
per client.

The canonical item — the three legs, the operations problem, the SRE research and the
decisions that are the owner's — is
`~/Documents/discord-bot/.claude/backlog/servidor-llave-en-mano-personas-alex.md`.
**It is not restated here.** What this item owns is the one AIRE-shaped piece it names.

**AIRE is the delivery vehicle**, and it already carries both halves the product sells:

| What the product needs | What AIRE already has |
|---|---|
| A capped, revocable key per client | `aire_token` with `budget_usd`/`spent_usd`, verified biting: `402 token_budget_spent`, then `401` after revoke ([#32](32-the-nickname-door.md) slice (d)) |
| Evidence of what was consumed | Both halves of every gateway turn mirrored to append-only `aire_gateway_log` ([#30](30-the-gateway-door.md)), and the app column now names the consumer ([#33](33-consumers-should-name-themselves.md)) |

## The small piece that is actually missing

**The till only rings for INVITED keys. A caller who brings their own Anthropic
credential is relayed intact and never billed, never capped, never counted.**

Verified in the source on 2026-08-15, not inferred:

- `gateway.py:109` — `holder = getattr(request.state, "holder", None)  # an invited key (#32), or nobody`.
  The `bank()` closure at `gateway.py:96` is built **only** when a holder exists; with no
  holder the turn is relayed and nothing is banked.
- `lending.py` says it in its own docstring: *"The gateway door is auth-pass-through by
  default: the caller's credential rides upstream and AIRE spends nothing."*

That default is correct as a *cost* stance — AIRE genuinely spends nothing — but it makes
the pass-through caller **invisible as a customer**. There is no ceiling to sell, no usage
to show, and no lever to cut off a client who stops paying.

Metering and capping the caller who brings their own credential is what turns AIRE from a
door into a product, and it is what enables the **zero cost-of-goods model**: the client
supplies their own Anthropic key, AIRE supplies the persona, the cap, the evidence and the
operation. No token resale, no margin on someone else's inference, no exposure to a price
change upstream.

Note the asymmetry that makes this cheap: the *transcript* already lands in
`aire_gateway_log` for pass-through turns. What is missing is not observation — it is
**accounting and enforcement on top of an observation that already happens**.

## Canonical path to reuse (Art. 6)

Nothing new gets invented. The pieces exist and are separately verified:

- `pricing.py` already converts a turn's `usage` into dollars.
- `tokens.py` already holds `budget_usd`/`spent_usd` per nickname and already produces the
  `402`.
- The `bank()` closure in `gateway.py` is already the seam where a turn pays.

The change is to give the pass-through caller an identity the same way the invited caller
has one, and to run the same `bank()` against it — a ceiling that **counts and cuts off**
without AIRE ever holding the credential. The header that names the consumer already ships
(`x-aire-project`, [#33](33-consumers-should-name-themselves.md)); whether that is the
identity or whether a client gets a real AIRE token that carries no lent credential is the
design question this item opens.

Closest neighbour, and deliberately **not** the same item: [#28](28-per-token-budget.md)
is about capping the keys AIRE *lends to* — it is Done for invited keys and still open for
the two CONSTANT keys. This item is about the callers AIRE lends **nothing** to.

## The credential blocker this does not solve

Related and worth naming so it is not conflated: **`AIRE_LEND_API_KEY` is still empty.**
`server/infra/lib/secrets.sh:48` provisions only `AIRE_LEND_OAUTH_TOKEN`, filled from
`CLAUDE_CODE_OAUTH_TOKEN` — so what AIRE lends to invited keys today is the OAuth of the
**Claude Max subscription Bernard's employer pays for**. `lending.py` already prefers the
metered slot in code and documents why (revocable without touching the subscription); the
slot is wired and unpopulated.

Metering the pass-through is what makes that blocker *avoidable* rather than *solved*: a
client on their own credential never touches the lent slot at all. Minting the metered key
remains Bernard's atom, tracked in [#32](32-the-nickname-door.md) and in the canonical
item's blocker list.

## The decision that's the owner's

- **Whether a paying client brings their own Anthropic key** (zero cost of goods, no terms
  exposure) **or AIRE resells tokens with margin.** This item makes the first option
  buildable; it does not choose it.
- **The ceiling numbers.** Same family as [#23](23-the-budget-cap-lies-twice.md),
  [#25](25-no-cumulative-ceiling.md), [#28](28-per-token-budget.md) — do not invent the
  dollar figures.
- Whether pass-through stays available **uncapped** for Bernard's own consumers while
  client keys are metered.

## Status / next step

Not built. Nothing here is urgent on its own — it becomes the critical path the moment a
client exists who is not Bernard.

1. Decide the identity of a pass-through caller (token without a lent credential, vs.
   `x-aire-project` header).
2. Run the existing `bank()` against it and confirm the `402` bites a caller carrying their
   own credential — measured from outside the droplet, the way [#32](32-the-nickname-door.md)
   slice (d) was, since that slice shipped blind and was caught only by walking it.

See the canonical item at
`~/Documents/discord-bot/.claude/backlog/servidor-llave-en-mano-personas-alex.md`,
and [#32](32-the-nickname-door.md) (the nickname door and its slice (e), where the lending
seam was built).
