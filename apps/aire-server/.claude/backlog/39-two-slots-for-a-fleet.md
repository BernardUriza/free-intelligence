# Two slots for a fleet — the pool that fits the box does not fit the consumers

Status: **Proposed** — a capacity/cost question, not a bug
Proposed: 2026-08-22 by Claude (reviewing discord-bot's stage-2 route before its
flag is ever flipped)

## What it is

`engine/pool.py` holds **`POOL_MAX = 2`** live clients, and that number is not
arbitrary — it is measured and correct for the box it runs on:

> *"ONE live client is 129 MB and the droplet has ~180 MB free, so POOL_MAX=8 was
> a latent OOM (8 × 129 MB ≫ 458 MB) — 2 is what the RAM actually holds."*

The same file explains what an eviction costs:

> *"the prompt cache AIRE pays for lasts 1h (`ephemeral_1h`) … a resumed turn then
> re-paid `cache_creation` (17× `cache_read`)."*

Both facts are right. The problem is what happens when they meet a consumer whose
unit of memory is **a chat**, not a project. AIRE's own design encourages exactly
that: casita-per-chat is what #36's thin birth is FOR, and og118, Fénix and
discord-bot all now name a casita per conversation. So the pool's key space grew
from "a handful of projects" to "every live conversation in the fleet", while the
pool itself stayed at two.

Past two concurrently-warm conversations, every turn is a **pool miss**: a new
`claude` subprocess, a `resume=` from Postgres, and the system prompt re-cached
from cold. AIRE's own receipt for that is on file — a single-sentence turn on a
fresh session cost **$0.107**, of which 17,375 tokens were cache-creation for the
system prompt ([[ssh-is-a-missing-endpoint]]). discord-bot's persona is ~14k
tokens on its own, and its `session_pool.py` measured that reuse drops a warm turn
to ~500–2k tokens. That gap is the whole prize, and a 2-slot pool hands it back
whenever a third conversation speaks.

## The measurement — taken 2026-08-22, and it changes the verdict

The deciding number is **distinct casitas active inside one hour**, against
`POOL_MAX=2`. Both doors were bucketed by hour through the front's read-only SQL
console (`aire_reader`, no write path involved).

**The ENGINE door today** (`claude_session_store` — the door that HAS the pool),
peak hours across its whole life:

| hour | distinct casitas | entries |
|---|---|---|
| 07-21 04 | **4** | 128 |
| 08-21 18 | 3 | 84 |
| 08-20 20 | 2 | 73 |
| everything else | 2 or 1 | |

So the engine already **exceeds its two slots at peak**, but barely, and rarely —
today's fleet (og118, Fénix, the books) is a 1–2 casita workload with occasional
spikes to 3–4. On its own, that is a shrug.

**The GATEWAY door** (`aire_gateway_log` — discord-bot's traffic TODAY, which is
exactly the traffic that would move onto the engine's pool if stage 2's flag is
flipped), last 7 days:

| hour | distinct conversations | turns |
|---|---|---|
| 08-20 21 | **9** | 36 |
| 08-20 16 | 8 | 32 |
| 08-20 20 | 7 | 26 |
| 08-20 14 | 7 | 36 |
| 08-17 19 | 7 | 24 |
| 08-22 00 | 6 | 28 |

**The verdict this produces:** the item is NOT theoretical, and it is also not
urgent today. Nothing needs to change while discord-bot's flag is OFF. But the
flag is the event that makes it real — flipping it takes the peak hour from ~4
casitas to **~13** (9 + today's 4) against two slots, six times the pool. Every
turn beyond the two warmest would re-pay a cold system prompt, and discord-bot's
persona alone is ~14k tokens.

This is now a **precondition on stage 2**, not a background worry: the flag
should not go permanent until this ceiling is answered, alongside the two
blockers already named ([#38](38-the-model-is-ignored-on-a-warm-session.md) and
the memory-tool gap in discord-bot's own item).

## The second failure mode, if concurrency IS real

Slots are also the concurrency limit: `POOL_MAX` permits, `SLOT_WAIT_S=45`. A
third simultaneous turn waits 45s and then gets `slot_busy` → the consumer's 503.
discord-bot serializes its *judges* behind a semaphore for exactly this reason,
but its interactive turns have no such gate, and Discord happily delivers
messages from several channels at once. So the ceiling shows up first as latency
and then as a retry storm — and the retries land on the same two slots.

## Canonical path to reuse (Art. 6)

Nothing here should be invented before the measurement exists. When it does, the
options are ordered cheapest-first and every one of them is already a pattern in
this repo or its neighbours:

- **Do nothing** (the answer if concurrency is 1–2). Record the measurement and
  drop the item. This is a real outcome and probably the likeliest one.
- **Tune, don't grow.** `POOL_MAX` and `POOL_IDLE_S` are env knobs
  (`AIRE_POOL_MAX`, `AIRE_POOL_IDLE_S`) composed by provisioning
  ([[device-verb-protocol]]'s persistence model). A smaller idle window trades
  cache hits for slot availability; there may be a better point on that curve for
  a fleet than for one book-writing session.
- **Shrink the client, not the box.** 129 MB is a `claude` CLI subprocess. Any
  reduction there multiplies by POOL_MAX. Unexamined so far.
- **Grow the droplet.** `s-1vcpu-512mb-10gb` ($4/mo) → the next size is ~$6/mo,
  which the $20 ceiling absorbs — but [[do-budget]] prohibition 1 means **only
  Bernard authorizes it**, and a resize is a spend event, not a config change.
  Note the pre-authorized fallback in that rule is scoped to a provisioning run
  he asked for; this would not be one.
- **Let the consumer collapse its key space.** A casita per channel is a choice,
  not a law: a consumer could name a casita per PERSONA and keep the channel in
  the session id. That trades #36's per-chat living identity for pool locality —
  a product decision on the consumer's side, not an AIRE change.

## The decision that's the owner's

1. **Whether to spend on the droplet at all** — and that is not answerable before
   the concurrency measurement, which is why the measurement is step one.
2. **If not spending: which consumer gives up per-chat casitas**, or whether the
   fleet accepts cold turns as the price of immortal memory.
3. **Whether interactive turns need a runner-side gate** like discord-bot's judge
   semaphore, so backpressure queues politely instead of arriving as 503s.

## Status / next step

Not built, nothing broken, and **no consumer is riding it today** —
discord-bot's flag is OFF, og118 and Fénix name one model and a modest number of
live chats. This item exists so the ceiling is known BEFORE a flag makes it a
production surprise, which is the only reason it was found: it was read out of
the pool's own docstring while reviewing the consumer that would have hit it
first.

The measurement it asked for is **done** (above, 2026-08-22): the engine peaks at
4 casitas/hour today, and the traffic that stage 2 would add peaks at 9. The
remaining step is Bernard's call, and only when the flag is up for flipping.

See also [[do-budget]] (the $20 ceiling and its prohibition on unilateral spend),
[#36](36-the-living-casita-prompt.md) (casita-per-chat, which grew the key
space), [#38](38-the-model-is-ignored-on-a-warm-session.md) (the other
consequence of binding a session to a pooled client), and
[`docs/listener-doctrine.md`](../../server/docs/listener-doctrine.md).
