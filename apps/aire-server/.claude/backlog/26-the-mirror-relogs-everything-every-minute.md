# The mirror re-reads everything every minute, and its log lies about idle silence

Status: **Fixed 2026-08-20** (`c9d707b`) — Bernard picked option (b), the mtime
cache: `/var/lib/aire/mirror-cache.json`, a RECONSTRUCTIBLE stamp file (losing it
re-reads once, uuid-dedup absorbs it), files stamped only after Postgres holds
their entries, deleted transcripts pruned. `offered` now counts only what was
re-shipped, so the idle minute is silent as the docstring promised.
Proposed: 2026-07-20 by Claude (found auditing the parallel-books E2E)

## What it is

`aire.log` shows `SESSION-MIRROR offered 437 entries from 2 door sessions` **every
single minute**, unchanged, on idle minutes where nothing was written. Two
problems behind that line:

1. **The log lies.** `mirror.py`'s own docstring promises *"logs to the file only
   when it actually offered entries, so an idle minute stays silent."* It never
   stays silent: `offered` counts every entry it RE-sends, not the entries that
   were actually new. `if offered:` is therefore always true, and the file fills
   with an identical line a minute forever — noise the broom/logrotate then has
   to sweep. A log that claims silence and never delivers it is a small Art. 2
   violation (the doc describes behaviour the code doesn't have).

2. **It's O(total history) per minute.** Every run does
   `for path in glob("*/*.jsonl")` → `read_entries(path)` parses each transcript
   **in full** → `store.append(key, all_entries)` hands the whole file to the
   dedup INSERT. The uuid `ON CONFLICT DO NOTHING` keeps Postgres correct, but the
   droplet still re-reads, re-parses, and re-ships the ENTIRE transcript history
   of every SSH-door session every 60 seconds. On a 512MB box this cost grows
   without bound as the books grow — today 437 entries, tomorrow every session
   ever opened.

## Canonical path to reuse (Art. 6) — and the wrinkle that makes it YOURS

The obvious fix (a per-file offset/watermark, or an mtime cache: skip a file
that hasn't changed) collides with a DELIBERATE decision written into
`mirror.py`: *"Idempotent by the store's uuid-dedup, so re-reading whole files is
safe and NO local offset state exists to lose."* The no-state design was chosen
on purpose — simplicity and crash-idempotence over efficiency.

Three ways to make the log honest, each touching something that is yours:
- **(a)** `store.append` returns how many rows it actually inserted → the mirror
  counts truth. But `store.py` is the upstream-diffable exempt copy (Art. 6, the
  thirty-line law's one exception) — changing its signature breaks that.
- **(b)** an mtime cache in the mirror → contradicts the written no-offset-state
  decision. It IS reconstructible (a lost cache just re-reads once, still
  idempotent — like the client pool is "hot cache, not truth"), so it may be
  philosophically consistent. Your call, not mine.
- **(c)** a `SELECT count` to compare → forbidden: the mirror lives in the
  write-only `server/` half ([[write-only-daemon]]).

## The decision that's the owner's

Whether the no-offset-state purity is worth an O(history)/minute mirror and a
log that can't keep its silence promise — or whether an mtime cache (option b)
is the reconstructible-cache exception that keeps the philosophy while fixing
both. This is exactly the "don't override his architecture" case: the no-state
design is a written decision; I report the cost and leave the fork to Bernard.

## Status / next step

Not built. Minimum honest step once the fork is picked: make `offered` count
only genuinely-new entries so the idle minute is silent as the docstring already
promises. The efficiency half rides on the same decision.
