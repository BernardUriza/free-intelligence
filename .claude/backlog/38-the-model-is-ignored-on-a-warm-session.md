# The `model` a turn asks for is silently ignored on a warm session

Status: **Fixed 2026-08-22** (`21f5ee7`) — measured broken, measured fixed
Proposed: 2026-08-22 by Claude (found while wiring discord-bot's stage 2 against
the live gate; the consumer routes a model PER TURN by severity, so it hit the
lie on its second turn)

## What it is

The door accepts `model` per turn (#29, `a40f389`) and the result reports the
model that answered. On a **cold** session that contract holds. On a **warm**
one it does not, and it fails the worst way available — silently.

Measured live against `gate.bernarduriza.com`, two turns, one session:

```
requested: claude-haiku-4-5-20251001  → answered: claude-haiku-4-5-20251001
requested: claude-sonnet-4-6          → answered: claude-haiku-4-5-20251001
```

No error, no warning, no `422`. The caller asked for a different model, was
told nothing, and got the old one.

Root cause is one seam: `engine/core.py::_client_for` builds `ClaudeAgentOptions`
only on a **pool miss**. So `model`, `mode` and `tools` bind at client BIRTH and
hold for the pool's idle life (`AIRE_POOL_IDLE_S=3300` — about 55 minutes). Every
later turn on that session reuses the client and its frozen options; the new spec
is simply never consulted.

**Why this belongs to the #23/#31 family and not to a backlog of nice-to-haves:**
the door's whole promise is that its receipts are real. #23 was a budget cap that
cut a turn and returned an empty success; #31 was a burned pool returning a
lying green. This is the same shape at the options seam — a request that cannot
fail because it is never read. Rule 22's test applies verbatim: *if the thing I
am verifying were completely broken, would this still look green?* It would, and
it did.

## Who is already hurt by it

- **discord-bot (stage 2, flag OFF).** `persona_runner/routing/` picks
  Haiku/Sonnet/Opus per turn by preset + severity + a 24h Opus budget. On the
  AIRE route an Opus escalation for a severe turn — the exact turns that matter,
  where a vulnerable user said something serious — would be answered by whatever
  model the session started with, an hour ago. Its own `model_diverged` warning
  now logs the divergence so it can never be silent on that side; the door still
  says nothing.
- **The judge is NOT affected**: a throwaway session per call means a fresh
  client every time, so the model is honoured. That asymmetry is itself the tell
  — the same field works or not depending on pool luck.
- **og118/Fénix are not affected today** because they name one model, but they
  are one product decision away (a "think harder" button) from meeting it.

## Canonical path to reuse (Art. 6)

The repair already has a precedent IN this repo: #23's fix retires a poisoned
client rather than papering over it (`engine/turn.py`). Same instinct here —
the pool is a **cache of a spec**, so a spec change is a cache miss.

- **Compare the incoming `TurnSpec` against the one the pooled client was born
  with** (store it beside the client in the pool) and, when the material fields
  differ (`model`, `mode`, `tools`), REBIRTH the client with `resume=` so the
  memory is untouched and only the options change. Resume is already the
  mechanism the pool uses on a miss — nothing new is invented.
- **The cheaper half-step, if a rebirth per divergence is judged too expensive**
  (a rebirth pays the system prompt's cache-creation again — measured at ~$0.107
  for a fresh session in [[ssh-is-a-missing-endpoint]]): make the door **refuse**
  the request instead of ignoring it — a `422` naming the session's bound model.
  A loud refusal is worth more than a quiet wrong answer, and the consumer can
  then decide to open a new session itself.
- **Either way, never keep the current behaviour silent.** If the field is
  accepted it must bind; if it cannot bind it must error. Accepting and dropping
  is the only outcome that is not allowed.

## The decision that's the owner's

1. **Rebirth vs refuse.** Rebirth is transparent and costs a cache-creation per
   model switch; refuse is free and pushes the session-management decision to
   the consumer. (A third option — bind the model per turn without touching the
   client — is not available: the SDK pins it at client construction.)
2. **Which fields count as material.** `model` clearly. `tools` and `mode` have
   the same defect and the same fix, but widening them mid-session has a
   security flavour (#37's dial) that argues for refuse-only there.
3. **Whether the pool's idle window (55 min) should shrink**, which would reduce
   the blast radius of any frozen spec but costs cache hits.

## Status / DONE

Bernard picked **rebirth** the same day, and it shipped in `21f5ee7`:

- `Engine.spec_of` remembers the shape each pooled client was born with;
  `_rebind` (called by `turn.py::_attempt` BEFORE it takes a client) drops a
  client whose shape no longer matches, and `_client_for` rebuilds it with
  `resume=` — the transcript untouched, only the options new.
- It never closes a client under someone else's turn: an in-flight turn holds
  the key's lock, so the rebind waits on it. A turn that starts inside that
  window keeps the old shape and the next turn corrects it — the divergence is
  bounded to ONE turn instead of an hour.
- `_drop` is now the single way a client leaves the pool, so the retire (#23)
  and the rebind cannot forget half its state.

**The receipt** — the same probe that found the lie, run against
`gate.bernarduriza.com` after the deploy, three turns on ONE session:

```
requested: claude-haiku-4-5-20251001  → answered: claude-haiku-4-5-20251001
requested: claude-sonnet-4-6          → answered: claude-sonnet-4-6
requested: claude-haiku-4-5-20251001  → answered: claude-haiku-4-5-20251001
```

Six tests in `server/tests/test_rebind.py`, including the one that matters most:
the first version of that file **passed with the fix removed from `turn.py`**,
because it exercised `_rebind` directly and proved the mechanism instead of the
wiring. The added test asserts the real turn path rebinds before it takes a
client, and it goes red when the call is deleted.

Two extractions the thirty-line law forced, both real concepts and not shards:
the detached turn's draining moved into `detach.py` beside the rest of
fire-and-forget, and the two spend ceilings became `Ledger` in `ledger.py`.

See also [#23](23-the-budget-cap-lies-twice.md) and
[#31](31-credential-failover.md) (the same lying-green family),
[#29](29-grow-the-door-per-turn.md) (where `model` was added), and
[#37](37-the-mode-dial-is-coarse.md) (the neighbouring seam — both are about a
turn's options not being as per-turn as they look).
