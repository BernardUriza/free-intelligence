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
| 15 | **The front repo** — the PHP of EC-GPS as a separate Next.js project: ALL database reads live there (see `.claude/rules/write-only-daemon.md`). First tenant: the monster (DFG view, evicted from this repo at `f40e21a`) | **Done 2026-07-13** — [`aire-front-seed`](https://github.com/BernardUriza/aire-front-seed), [live on Container Apps](https://aire-front.greendune-53f1f4af.eastus2.azurecontainerapps.io). Tables/browse/SQL console/the monster, all SSR, all read-only. Behind HTTP Basic, connecting as `aire_reader` (`GRANT SELECT` only — it cannot write even with every app-level wall bypassed). **What this repo must honour: create `claude_session_store` as role `aire`**, or `ALTER DEFAULT PRIVILEGES` will not reach it and the console goes blind to the transcripts |
| 16 | **The first verb — MKDIR (the casita simulation).** Proposed by Bernard 2026-07-13: a device line asks the daemon to create a workspace folder — simulating the per-project `cwd` home the agent mode will get (his Mac-in-the-cloud analogy). Design notes: (a) command = event — append the line to the log FIRST, execute after, append the result (`FOLDER-CREATED …`); (b) stable homes derive from `uuid5(name)` (same name → same casita, `aire/keys.py` already does this), `{timestamp}_{uuid}` only for disposable scratch; (c) security: verbs are gated by AIRE_VERB_TOKEN (long secret, Mac + /etc/aire/env only, redacted from the log) so the port stays internet-open | Done — MKDIR verb live 2026-07-13; the demo device asks on its own (random, max 2/hour, rules in the device) |
| 17 | **Make the SSH door deathless too.** The interactive `claude` CLI on the droplet (tmux + the TUI, see README "Two doors") stores its transcript on the droplet's DISK — kill the box and that conversation dies, which is exactly what the litmus test forbids. Investigate wiring the CLI's session mirror into the same Postgres store the engine uses (the SDK's `--session-mirror` flag is already visible in the engine's subprocess argv), so both doors write to one memory | Proposed |

---

**The only one that matters today is #5.** Everything else is plumbing until chapter 2
remembers chapter 1.
