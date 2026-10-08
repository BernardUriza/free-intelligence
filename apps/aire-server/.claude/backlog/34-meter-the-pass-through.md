# Meter the pass-through — the caller with their own credential is invisible to the till

Status: **Done** 2026-08-21 (`f0195a6`) — measured live through the real gate
Proposed: 2026-08-15

## What it is

This is **AIRE's slice of a product decision that lives elsewhere**: Bernard wants an
income source of his own that takes him out of the 1099/W2 cycle and into owning a
business with revenue. The product is a turn-key Discord server — a client's own server,
with bots whose persona Alex Nava designs, delivered with a capped, revocable AIRE key
per client.

The canonical item — the three legs, the operations problem, the SRE research and the
decisions that are the owner's — is
`~/Documents/free-intelligence/apps/server-bot/.claude/backlog/servidor-llave-en-mano-personas-alex.md`.
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
`server/infra/lib/secrets.sh` provisioned only `AIRE_LEND_OAUTH_TOKEN` (until 2026-08-22 — it now derives `AIRE_LEND_API_KEY` from the metered key instead), filled from
`CLAUDE_CODE_OAUTH_TOKEN` — so what AIRE lends to invited keys today is the OAuth of the
**Claude Max subscription Bernard's employer pays for**. `lending.py` already prefers the
metered slot in code and documents why (revocable without touching the subscription); the
slot is wired and unpopulated.

Metering the pass-through is what makes that blocker *avoidable* rather than *solved*: a
client on their own credential never touches the lent slot at all.

🔒 **Not a blocker today — DECIDED 2026-08-17 by Bernard: the OAuth token stays and no
metered key gets minted. Do not re-propose it** (Art. 7, decision recorded in
[#32](32-the-nickname-door.md)). The paragraph above describes serving third parties; the
door has **zero users who are not Bernard**, so it is self-use, not resale. The trigger
that reopens it is the first stranger requesting access by email — not the arrival of a
paying client, and not a session that reads this file and finds an empty variable.

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

**Done 2026-08-21** (`f0195a6`). Both open questions closed:

1. **Identity is a real `aire_token`**, not the `x-aire-project` header (a header with no
   secret cannot bill or cut anyone off; the header stays observability-only, #33). The
   key rides in the new AIRE-addressed **`x-aire-key`** header (Claude Code style:
   `ANTHROPIC_CUSTOM_HEADERS`, leaving the Bearer slot for the caller's own OAuth), or as
   the Bearer next to an `x-api-key`. One function decides (`gateway._outfit`): shed the
   AIRE key, and if a credential of the caller's own survives it rides — metered
   pass-through, nothing lent; if nothing survives, the key is invited and AIRE lends
   (#32) as before. The 402, the concurrency slot, and the `bank()` closure are the same
   code the invited path already had; the biller moved to `tokens.biller()`. The mirror
   gained a `holder` column, so consumption is attributable per key, per turn.

2. **Measured from OUTSIDE the droplet, 2026-08-21**, the way slice (d) demanded:
   - A seeded key `metertest-34` (budget $0.001) + Bernard's own OAuth as the caller's
     credential + `x-aire-key`: **200**, a real reply, `spent_usd` banked $0.000046.
   - The can't-be-fooled receipt that nothing was lent: an **invalid** `x-api-key` beside
     the key answered Anthropic's own **401 "API key is invalid"** — the caller's dead
     credential rode upstream; a lending path would have answered 200.
   - A 243-output-token turn crossed the ceiling; the next turn answered
     **402 "AIRE: metertest-34 has spent its budget"** — the cutoff lever, live.
   - Anonymous pass-through (no AIRE key): still 200, unmetered, invisible — Bernard's
     own consumers stay uncapped until he hands them keys.
   - The mirror attributed every request row to `holder = metertest-34`; the test key was
     revoked after the walk.

The evidence leg rendered too (`56acd50`): `/gateway` surfaces the key column beside the
app column, in conversations and loose exchanges — verified in the real browser on
aire.bernarduriza.com, the three metered turns attributed to `metertest-34`, everything
anonymous showing "—". `npm run attack` green. The remaining owner decisions below stand
unchanged.

See the canonical item at
`~/Documents/free-intelligence/apps/server-bot/.claude/backlog/servidor-llave-en-mano-personas-alex.md`,
and [#32](32-the-nickname-door.md) (the nickname door and its slice (e), where the lending
seam was built).

## Correction against the box (2026-08-22)

This item recorded that no metered key would be minted while the door had no
users but Bernard. **A metered key exists on the droplet today** —
`ANTHROPIC_API_KEY_FALLBACK`, a real `sk-ant-` value — armed as the rotor's
third slot (#31), which is a different use than the lending this item settled.
The decision recorded here was about what the DOOR lends, and it still stands:
the box lends `AIRE_LEND_OAUTH_TOKEN`, not the metered key. **Reversed 2026-08-22**: it lends the metered key, verified with a real invited turn.

Recorded because the two documents disagreed with reality in opposite
directions and neither said so — [[40-every-guard-fails-quietly]] is the item
about safeties that report nothing, and a document is a safety.
