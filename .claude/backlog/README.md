# Backlog — AIRE

## The mirror (so the memory is never lost)

| # | Item | Status |
|---|------|--------|
| 1 | Copy the SDK's official `postgres_session_store.py` and run `run_session_store_conformance` against it (14 contracts) | Proposed |
| 2 | Bring in `hosting/server.py` from the official cookbook and **wire the `session_store`** into it (which it lacks) | Proposed |
| 3 | `project_id` → `cwd` + `CLAUDE_CONFIG_DIR` per project (the cookbook hardcodes it to `/app`) | Proposed |
| 4 | Deterministic `uuid5` from the name → goodbye `hosting_session_map.json` and the in-RAM dict | Proposed |
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
| 12 | `Stop` hook → `git commit && push` of the corpus when each job closes | Proposed |
| 13 | Semantic search over the sessions (pgvector) | Idea |
| 14 | PR to Agno: add `session_store` to their `ClaudeAgent` (41k ⭐, it's only a few lines) | Idea |

---

**The only one that matters today is #5.** Everything else is plumbing until chapter 2
remembers chapter 1.
