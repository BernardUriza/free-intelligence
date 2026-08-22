# The gateway mirror stores the whole conversation on every turn

Status: **Proposed** — measured, not urgent, and growing every day
Proposed: 2026-08-22 by Claude (measured on the live Azure Postgres during the
structural review, [#40](40-every-guard-fails-quietly.md))

## What it is

`aire_gateway_log` appends both halves of every proxied exchange — the request
body and the assembled response — as `jsonb`. That is right: the gateway sees
raw API turns and the log is the truth ([[log-is-the-truth]]).

But the **request** body of a conversational client is not one turn. The
Messages API is stateless, so Claude Code re-sends the ENTIRE conversation on
every call. Turn 20 carries turns 1–19 again, verbatim, and the mirror stores
all of it — beside the nineteen rows that already hold the same bytes. The
accumulation is quadratic in a session's length, and it is invisible because
each individual `INSERT` looks reasonable.

## The measurement (live, 2026-08-22)

Fifteen days of real traffic on `development-pg-n66dz`:

| | rows | bytes |
|---|---|---|
| `aire_gateway_log` **request** | 584 | **64 MB** |
| `aire_gateway_log` **response** | 583 | 8 MB |
| `claude_session_store` (the actual memory) | 1,249 | 4 MB |
| `aire_log` (the pen) | 2,826 | 1.3 MB |

- **3.4 MB/day**, → **~102 MB** at steady state inside the 30-day retention
  window the broom enforces.
- The request half is **8× the response half**, and the whole table is **12× the
  session store it sits beside** — for the same conversations.
- The five largest single rows are requests of **1.7 MB, 1.5 MB, 822 kB, 803 kB
  and 685 kB**, all `claude-opus-4-7`. Those are context windows, replayed.

The costs are real but not yet loud: storage on the shared Azure server, a
`gatewaySessions()` view on the front that groups the whole table with no index
on `kind` (also filed in #40), and a broom that has to delete more every night.

## Why it matters more than the megabytes

[[do-budget]] states the law this lands on:

> *"Never watch only the cloud where the spend is frozen. The blind spot always
> opens over the thing that grows."*

DigitalOcean is frozen at $4/mo and watched nightly by costwatch. The Azure
Postgres is the thing that grows, and until #40 nothing watched its SIZE at all
— only that the broom's timer was alive. A broom that runs perfectly while the
input rate rises is a green light over a rising line.

## Canonical path to reuse (Art. 6)

Ordered cheapest-first; the first two are honest without changing the contract:

- **Measure before deciding.** A per-day size series on `aire_gateway_log` in
  costwatch (it already SSHes in nightly) turns this from a snapshot into a
  trend, and would have surfaced it without a review.
- **Mirror the request DELTA, not the replay.** The truth of turn N is the new
  message plus the parameters; turns 1..N−1 are already rows 1..N−1 of the same
  `session_id`. Storing the last message, the model, the params and a count/hash
  of the prior context keeps every fact and drops ~7/8 of the bytes. This does
  NOT violate [[log-is-the-truth]] — the log stays append-only and complete; it
  simply stops storing the same bytes N times. The front's gateway views already
  key on `session_id`, so a reader can reconstruct the full context by reading
  the session's rows in order, which is what an append-only log is for.
- **Compress the body column.** `jsonb` is already TOAST-compressed; storing the
  raw text `EXTERNAL`/`lz4` or moving to `bytea` + zstd would cut it further
  without any semantic change. Cheapest to implement, keeps every byte, does not
  fix the quadratic shape.
- **Shorten `AIRE_GATEWAY_RETENTION_DAYS`.** The knob already exists and is
  independent of `AIRE_RETENTION_DAYS` (#6). Blunt, loses evidence, but it is
  one env var and the retention window for raw API turns need not equal the
  pen's.

## The decision that's the owner's

1. **Whether the gateway mirror is EVIDENCE or MEMORY.** If it is evidence for
   metering (#34's per-key attribution), the delta is plainly enough. If it is
   meant to be a second, independent memory of every turn, the replay has a
   reason and the answer is compression plus a shorter window instead.
2. **Whether a size trend belongs in costwatch** as a threshold that goes red,
   the way DO spend does, or only as a printed number.

## Status / next step

Not built, nothing broken, and the broom is holding at 30 days. The next step is
the measurement leg — a nightly size line in costwatch — because it is a few
lines, it costs nothing, and it is the difference between knowing the rate and
finding out from a bill.

See also [#40](40-every-guard-fails-quietly.md) (the silent-degradation family
this belongs to), [#6](../backlog/README.md) (the broom's gateway window),
[[do-budget]] (watch the thing that grows) and [[log-is-the-truth]].
