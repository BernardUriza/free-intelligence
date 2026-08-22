# The gateway mirror stores what the log already holds

Status: **Done 2026-08-22** — measured, then measured AGAIN because the first
reading was wrong, then fixed and re-measured against every real row
Proposed: 2026-08-22 by Claude (during the structural review,
[#40](40-every-guard-fails-quietly.md))

## What it is

`aire_gateway_log` appends both halves of every proxied exchange as `jsonb`.
That is right: the gateway sees raw API turns and the log is the truth
([[log-is-the-truth]]).

But the Messages API is stateless, so a conversational client re-sends
**everything** on every call — turns 1..N−1, the whole `system` array, and every
tool's full JSON schema — and the mirror stored all of it, beside the rows that
already held the same bytes. Each individual `INSERT` looks reasonable, which is
exactly why it was invisible.

## The first measurement (live, 2026-08-22) — and what it got WRONG

Fifteen days of real traffic on `development-pg-n66dz`:

| | rows | bytes |
|---|---|---|
| `aire_gateway_log` **request** | 584 | **64 MB** |
| `aire_gateway_log` **response** | 583 | 8 MB |
| `claude_session_store` (the actual memory) | 1,249 | 4 MB |
| `aire_log` (the pen) | 2,826 | 1.3 MB |

The request half is **8× the response half** and **12× the session store beside
it**, growing **4.2 MB/day** → **~127 MB** at the 30-day retention window.

Those numbers held. Three claims written beside them did not, and they are
recorded here because a corrected number is worth more than a tidy page:

1. **"~7/8 of the bytes"** — the estimate for what a delta would save. The real
   figure is **52%**. Written before anything was replayed.
2. **"The five largest rows are context windows, replayed"** — false. The largest
   request carries **ONE turn of 1,597 KB**: a single huge message, not history.
   That is not redundancy at all, and cutting it would be loss.
3. **The diagnosis itself.** "Quadratic in a session's length" assumed long
   conversations. The replay found **237 distinct sessions across 585 rows** —
   most conversations are one or two turns, so history is the *minor* half.

The dominant redundancy was somewhere else entirely, and only a full replay
showed it: across the whole history there are **33 distinct `system` arrays and
9 distinct tool sets**, stored **585 times**. Composition of the 60 largest
requests: `messages` 76.9%, `system` 16.8%, `tools` 9.1%.

## What shipped

`gateway_condense.py` splits a request into what is NEW and what the log already
holds; `gateway_store.py` (the schema and pool, cut out of `gateway_mirror` when
it started carrying three concepts) keeps the repeated values once:

- **`messages`** — only the last is kept, and the row announces the count it did
  not repeat (`$elided`). The rest are the earlier rows of the same
  `session_id`, which is what an append-only log is for. The front already
  agreed: every gateway view pulls `$.messages[last]`, and its own comment calls
  the rest *"history the caller resent"*.
- **`system` / `tools`** — content-addressed into a new `aire_gateway_blob`
  (`fingerprint` PK), written once with `ON CONFLICT DO NOTHING`, referenced by
  fingerprint from the row. A fingerprint is a JOIN, not a search.
- **Never truncate.** A huge single message stays whole; those bytes exist
  nowhere else.
- **A failed blob write inlines the value instead** (`inline()`). A fat row is
  right; a reference to a row that was never written is a dangling pointer the
  front cannot repair.

Keying `system`/`tools` per SESSION was measured too, and gives only **1.50×** —
because with 237 short sessions that is 237 copies of the same handful of
values. Global content-addressing gives **2.07×**. The measurement chose the
design.

## The re-measurement (all 585 real rows replayed through the shipped code)

```
stored today             63.73 MB
rows as a delta          29.34 MB
+ aire_gateway_blob       1.44 MB   (42 distinct values)
= new total              30.78 MB   (48.3% — 2.07x smaller)
RECONSTRUCTION FAILURES:  0         (system, tools and the last message all
                                     came back byte-for-byte)
growth: 4.23 MB/day -> 2.04 MB/day
at the 30-day window: 127 MB -> 61 MB
```

Lossless is the claim that mattered, so it was tested as a claim: every row was
reconstructed from the delta plus the blob table and compared against the
original.

## Why it mattered more than the megabytes

[[do-budget]] states the law this landed on:

> *"Never watch only the cloud where the spend is frozen. The blind spot always
> opens over the thing that grows."*

DigitalOcean is frozen at $4/mo and watched nightly. The Azure Postgres is the
thing that grows, and nothing watched its SIZE — only that the broom's timer was
alive. A broom that runs perfectly while the input rate rises is a green light
over a rising line.

## The trap this introduced, and how it was closed the same day

Content-addressing creates a reference, and a reference can dangle. Two ways,
both closed:

- **The broom.** `sweep.py` now reclaims `aire_gateway_blob`, but only
  fingerprints that **no surviving row references** — the `NOT EXISTS` is the
  load-bearing half, and it is mutation-tested: with the guard removed, the test
  that says a referenced blob survives goes red. It runs AFTER the log sweep, so
  a row deleted above is a reference released here. Its own `NOT SELECT` law was
  re-stated rather than quietly broken: this read renders nothing and gates a
  delete, which is the kind [[write-only-daemon]] sanctions.
- **The daemon's cache, which was the sharper one.** `gateway_store._stored`
  claimed "the database still holds this" and could not verify it. A process that
  wrote a fingerprint, went quiet past the retention window, and used it again
  would reference a blob the broom had legitimately reclaimed. Dropping the cache
  outright was measured first and rejected on evidence: a no-op INSERT on an
  already-open pooled connection costs **24 ms**, and it sits on the relay's
  critical path — two blobs would be ~50 ms on every request's time to first
  byte. So the cache **expires** (`AIRE_BLOB_TTL_S`, 6h against a daily sweep):
  anything used inside the TTL has rows far inside the retention window, so the
  broom cannot touch it, and anything older is re-asserted for one 24 ms INSERT.

## The watch that should have found this (done 2026-08-22)

`infra/growth.py` runs from costwatch's nightly SSH block, beside `wall.py`:
the size of the whole database and of each table, plus **MB/day measured over
each table's own live window**, red past a ceiling (`AIRE_DB_CEILING_MB`, 250).
Proven able to go red before its green was trusted — the ceiling forced to 1 MB
exits 1 against the live pen.

First reading, on the real database:

```
database: 66.9 MB (ceiling 250 MB)
  aire_gateway_log        51.31 MB     3.38 MB/day over 15.2d
  claude_session_store     5.95 MB     0.18 MB/day over 33.1d
  aire_log                 1.32 MB     0.04 MB/day over 30.3d
  aire_casita              0.27 MB   (new today)
  aire_gateway_blob        0.03 MB   42 distinct values
```

Two things that reading makes visible and nothing did before. The gateway's
3.38 MB/day is still the HISTORICAL average — the delta code is hours old, so
the number this watch exists to show is the one that falls over the next weeks.
And `claude_session_store` grows at 0.18 MB/day **with no broom at all**: it is
the one table retention deliberately never touches, because deleting it breaks
deathless sessions, so its growth is unbounded by design and this is the only
thing measuring it.

`scripts/check_law.py` was extended in the same commit: it globbed only the root
and `aire/`, so every provisioning script under `infra/` — and the gate itself —
was exempt from the law it enforces. Proven with a deliberate 35-line function in
`infra/`, which now fails the check.

See also [#40](40-every-guard-fails-quietly.md) (the silent-degradation family
this belongs to), [[do-budget]] (watch the thing that grows),
[[log-is-the-truth]] (append-only, and correcting means appending — including
correcting this page's own numbers) and [[verify-before-assuming]] Rule 0.
