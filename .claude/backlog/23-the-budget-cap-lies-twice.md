# The budget cap lies twice

Status: **Fixed 2026-07-20** (the silent kill and the poisoned client). The
ceiling's VALUE remains Bernard's open decision — see the fork below.
Proposed: 2026-07-20 by Claude (found while writing the whales book through the AIRE door)

## What shipped (`751e445`), verified live

A turn whose cost reaches the ceiling now emits a real `error` event and its
client is retired from the pool. Proven by lowering the cap to `$0.05` on the
droplet and forcing a cut — the turn stopped at `$0.1179` and answered:

```
event: error
data: {"type":"error","error":"budget_exhausted","detail":"the turn reached the
$0.05 ceiling and was CUT — its work may be incomplete. The spent client is
retired; send the turn again to continue."}
```

The next turn on that same session then ran normally (96 output tokens, a real
`Glob`, `$0.0177`) instead of dying sterile — the retirement works. The cap was
restored to `$1.00` and the probe data swept from the store.

## What it is

`AIRE_MAX_BUDGET_USD` (→ the SDK's `max_budget_usd`) does not behave the way this
repo documents, and when it fires the caller cannot tell.

**Lie 1 — it caps the CLIENT, not the turn.** `engine/core.py` states in a
comment: *"The SDK's `max_budget_usd` caps ONE turn."* Observed on the droplet
with the cap at `1.0`: a whales turn spent `$1.0073` and was killed mid-work;
**every subsequent turn on that same pooled client died instantly** — `output: 0`,
`cache_creation: 0`, no tool calls, and the *same* `$1.0073` reported again. The
ceiling is cumulative over the live `ClaudeSDKClient`, so a pooled client that
reaches it is permanently poisoned until evicted. Restarting `aire-server` (which
drops the in-RAM pool) restored service immediately — that is the proof.

**Lie 2 — the kill is silent and looks like success.** The turn ends with a
normal `result` event carrying `"text": ""` plus `done`. No `error` event, no
`BudgetExceeded` (that path only guards the *cumulative* `AIRE_MAX_SPEND_USD`
BEFORE a turn starts). A client cannot distinguish "the agent finished and had
nothing to say" from "you were cut off after paying a dollar". Both whale
attempts billed `$1.0073` and wrote **zero files**.

## Canonical path to reuse (Art. 6)

The engine already inspects `usage.total_cost_usd` on every `result` to feed
`_spend_usd`. The same inspection can compare against the configured per-turn cap
and emit a real `error` event (the `BudgetExceeded` machinery and its SSE shape
already exist in `contract.py` / `server.py` — reuse it, don't invent a second
error path). Pool eviction on a poisoned client belongs next to `Pool.evict`.

## The decision that's the owner's

**Whether the cap is per-turn or per-session, and its value.** Today's $1.00
makes a long agent job (a book) impossible in one turn — the whales book only
shipped by splitting into four batches and restarting the service between them,
which is a workaround, not a design. Bernard's call, since it is spend
([[do-budget]] is his hard law): keep $1.00 and make batching a first-class
feature, or raise it for agent-mode jobs. Do not change the ceiling without him.

## Status / next step

(a) the honest `error` event and (b) the client retirement are **done and
verified**. What remains is only Bernard's spend fork above: at `$1.00` a long
agent job still cannot finish in one turn — the whales book shipped in four
batches. Either batching becomes a first-class feature (#22a's non-blocking
launch is its natural home) or the ceiling rises for agent mode.

Related: #22 (the endpoints SSH was covering) — a long agent job needs both a
non-blocking launch and a ceiling that does not silently eat it.
