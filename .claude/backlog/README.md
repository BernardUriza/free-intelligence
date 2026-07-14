# Backlog — AIRE

## The mirror (so the memory is never lost)

| # | Item | Status |
|---|------|--------|
| 1 | Copy the SDK's official `postgres_session_store.py` and run `run_session_store_conformance` against it | Done — `aire/store.py`; conformance suite green 2026-07-13 |
| 2 | An HTTP server with the `session_store` wired in (what the official cookbook lacks) | Done — `aire/server.py` (own server, cookbook as reference; auth still pending) |
| 3 | `project_id` → `cwd` + `CLAUDE_CONFIG_DIR` per project (the cookbook hardcodes it to `/app`) | Done — `Engine._cwd` + `AIRE_ISOLATE_CONFIG` |
| 4 | Deterministic `uuid5` from the name → goodbye `hosting_session_map.json` and the in-RAM dict | Done — `aire/keys.py` |
| **5** | **Tracer: chapter 1 → kill the container → chapter 2 reads chapter 1 from Postgres** | **Proposed** |

## The broom (so the garbage stays manageable)

The SDK **never deletes** and delegates retention to the adapter in writing. Nobody
has implemented it — not the cookbook, not Agno, not ArcReel. It is the cleanest gap.

| # | Item | Status |
|---|------|--------|
| 6 | Retention: per-project TTL, archive cold sessions, purge | Proposed |
| 7 | Scheduled backups (`pg_dump` + cron) | Proposed |
| 8 | Metrics: how much each project weighs, how many sessions, what they cost | Proposed |
| 9 | Compaction / summarization of old sessions before archiving them | Idea |

## What opens up because the database is yours

| # | Item | Status |
|---|------|--------|
| 10 | A page to view your sessions (it's a `SELECT`) | Proposed |
| 11 | Memory Tool (`memory_20250818`) → distilled facts in the same database | Proposed |
| 12 | Git as a user-layer tool: an MCP configured from OUTSIDE via the API, with the user's own account (personal or work) — AIRE itself never touches git; only then does `Stop` hook → commit/push make sense | Idea |
| 13 | Semantic search over the sessions (pgvector) | Idea |
| 14 | PR to Agno: add `session_store` to their `ClaudeAgent` (41k ⭐, it's only a few lines) | Idea |
| 15 | **The front repo** — the PHP of EC-GPS as a separate Next.js project: ALL database reads live there (see `.claude/rules/write-only-daemon.md`). First tenant: the monster (DFG view, evicted from this repo at `f40e21a`, parked in `~/Documents/aire-front-seed/`) | Proposed |

---

**The only one that matters today is #5.** Everything else is plumbing until chapter 2
remembers chapter 1.
