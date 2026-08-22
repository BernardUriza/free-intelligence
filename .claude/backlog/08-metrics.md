# Metrics: how much each project weighs, how many sessions, what they cost

Status: Proposed — split by feasibility after a 2026-07-20 data check
Proposed: 2026-06 (original backlog); refined 2026-07-20 by Claude

## What it is

A per-casita metrics view: weight, session count, and spend. The `/claude` view
already shows sessions + entries; this adds weight and cost.

## The 2026-07-20 data check — cost is NOT in the store

Trying to add a cost column, I checked the real jsonb before building (Loop Law):
**0 of 400 `claude_session_store` entries contain `total_cost_usd`.** The entry
types are `user`/`assistant`/`attachment`/`system`/`last-prompt`/`mode`/
`queue-operation` — the SDK transcript. `total_cost_usd` lives ONLY in the SSE
`result` event at turn time and is never persisted. So the front (which reads
only this table) cannot show cost today. The columns split three ways:

- **Sessions / entries** — DONE, already on `/claude`.
- **Weight** — BUILDABLE NOW in the front, read-only: `sum(length(entry::text))`
  or `pg_column_size` per `project_key`. Exactly what "how much each project
  weighs" asked for, and the data is already there.
- **Cost** — NOT buildable from current data. Requires the write path (server)
  to PERSIST the per-turn cost first. The engine already knows it (`_account`
  sees `total_cost_usd`), but there is nowhere durable it lands.

## Canonical path to reuse (Art. 6)

Weight: extend the existing `/claude` grouping query in the front's `db.ts` (the
one module that touches Postgres), one more aggregate, one more column. No new
surface.

Cost persistence: the engine writes; a reader shows. The pen already creates
tables as role `aire` (`claude_session_store`, `aire_device`), so an `aire_cost`
table is the same pattern. The correct figure is the MAX cumulative
`total_cost_usd` per session (cost is cumulative — verified 2026-07-20, backlog
#23), summed per project — NOT the raw sum, which would N-count.

## The decision that's the owner's

**Where cost persists.** It is a new write surface, so it is an architecture
call ([[write-only-daemon]] — the daemon owns its DDL): a dedicated `aire_cost`
table (queryable, clean) vs a `COST` line appended to `aire_log` (reuses the pen,
but the engine writes to the store, not the log) vs a synthetic cost entry in the
transcript (contaminates the SDK transcript — rejected). Recommend the table.
The weight column needs no decision and can ship on its own.

## Status / next step

Weight column: buildable now (front, read-only). Cost: blocked on the persistence
decision above, then a write-path change + the front read.

## Receipts (moved here 2026-08-22 from the index, which was the only place they lived)

Weight + sessions shipped `7e05a4e`, verified in the browser on `/claude`. Cost
stayed blocked by a measurement, not an opinion: a data check found
`total_cost_usd` is persisted in **0 of 400** entries, so the column has nothing
to read — it needs a write-path change plus the schema decision above, which is
Bernard's.
