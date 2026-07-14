# AIRE — context for agents

**A**rtificial **I**ntelligence **R**eflector **E**nvelope. An HTTP server that wraps
the Claude Agent SDK and mirrors each session's transcript to Postgres.

The story — the Mecano song, the EC-GPS blueprint, the log-is-truth science — lives in
[`docs/genesis.md`](docs/genesis.md); the competitive pitch in
[`docs/thesis.md`](docs/thesis.md). This file is only what an agent needs to ACT.

**The litmus test for every design decision** (from the genesis):

> *Does this give the agent a body back? Then no.*

Everything below was **verified against the source code of the installed SDK**
(`claude-agent-sdk` 0.2.116) or by observing the running system — never against
memory. To contradict anything here, verify it first the same way.

## The decisions, already made

1. **AIRE is a SERVICE, not a library.** You don't import it: you call it over HTTP.
   The SDK lives in one place, the Postgres credentials live in one place, any
   language can talk to it.
0. **THE SERVER IS THE INTERFACE — SSR, not a JSON API.** The central thesis. AIRE
   **returns server-rendered HTML that keeps writing itself** as the agent thinks
   (streaming HTML, not one-shot SSR). `GET /projects/avatar` → a page, with the agent
   working, live. No React, no npm, no build. This covers the LIVE page — painted
   from the engine's in-flight events, not from a database read. Browsing and
   analyzing STORED sessions is the front repo's job (decision #5).
2. **One database, one `project_key` per project.** The SDK's `SessionKey` already
   carries `project_key`; its docstring says *"Multi-tenant deployments should set this."*
3. **The memory (transcript) goes to Postgres. The work does NOT go to git — AIRE
   doesn't touch git.** Not yet: AIRE is not defined as a code agent. EC-GPS never
   used git either — artifacts were downloaded by hand for analysis, and **at this
   level that is the design, not a gap.** If git ever enters, it enters as a **tool
   configured FROM OUTSIDE, at the user layer** — an MCP wired in via the API with the
   *user's own account* (personal or work), never as an identity baked into the server.
4. **The container stores nothing.** `CLAUDE_CONFIG_DIR=/tmp`.
5. **This repo is WRITE-ONLY toward the database.** Every read — rendering,
   analytics, dashboards, session browsing — lives in a separate front repo (the
   PHP of EC-GPS, planned as Next.js; backlog #15). The one sanctioned exception
   is the SDK's `session_store.load()` for resume (the agent reading its own
   memory). Full law: [`.claude/rules/write-only-daemon.md`](.claude/rules/write-only-daemon.md).

## Reuse, don't rewrite

- **The Postgres store**: copied from the SDK's official
  `examples/session_stores/postgres_session_store.py` → [`aire/store.py`](aire/store.py)
  (two marked adaptations: uuid-dedup in `append()`, lazy-asyncpg factory).
  **Conformance suite green** (2026-07-13): all contracts of
  `claude_agent_sdk.testing.run_session_store_conformance` passed against local
  Postgres.
- **The HTTP server pattern**: `claude_agent_sdk/hosting/` in
  [claude-cookbooks](https://github.com/anthropics/claude-cookbooks) is the reference
  (FastAPI + SSE + Bearer auth). AIRE's [`aire/server.py`](aire/server.py) opens the
  axis the cookbook lacks: `POST /projects/{project}/sessions/{session}/messages`
  (the cookbook hardcodes one project, `cwd="/app"`). Names map to SDK UUIDs via
  `uuid5` ([`aire/keys.py`](aire/keys.py)) — no mapping table.

## Verified SDK facts (don't re-discover them)

- **`session_id` CAN be set.** `subprocess_cli.py:355` → `cmd.extend(["--session-id", ...])`.
  **No mapping table needed** from external id to SDK id.
- **`session_store` and `enable_file_checkpointing` are INCOMPATIBLE.** The SDK raises
  `ValueError` (`session_store_validation.py`): *"checkpoints are local-disk only and
  would diverge from the mirrored transcript."* → **No `rewind_files()`. The workdir is
  scratch; artifacts worth keeping are fetched by hand (decision #3).** The day git
  exists as a user-layer MCP, branches would take that role — not yet.
- **`session_store` is a mirror, not a replacement.** The subprocess keeps writing the
  JSONL to disk; the adapter receives **a secondary copy**. On resume, the SDK loads
  from the store and materializes it into a temp dir with `CLAUDE_CONFIG_DIR`.
- **`session_store_flush='eager'`** writes each entry immediately → no loss window if
  the container dies. `'batched'` is faster but can lose.
- **`continue_conversation` + `session_store` requires `list_sessions()`** implemented.
- **Only `append()` and `load()` are mandatory** in the Protocol; the other four are
  optional and the SDK probes them at runtime.
- **There are two distinct memories**: `SessionStore` (raw transcript) and the
  **Memory Tool** (`memory_20250818`, distilled facts, client-side → your same database).
- **`SandboxSettings`** confines the agent (bash sandbox, `excludedCommands: ["git"]`).
  The "container that doesn't self-modify" is **config, not infra**.
- **`Stop` hook** → where end-of-job actions go. (The old `git commit && push` idea is
  parked until git exists as a user-layer MCP — see backlog #12; today: nothing.)
- **`max_budget_usd`** → hard spend cap per query.

## Discarded routes (don't re-propose them)

- **Ephemeral VM with SSH** (the original `air-lite`): the Agent SDK reinvented with
  `boto3` + `paramiko`. Dead.
- **Persistent VM ("never terminate")**: reinvents git as storage and pays 24/7 rent
  for a disk that is a single point of failure. Dead.
- **Managed Agents** (Anthropic's hosted offering): the memory lives on their side, no
  `session_store`, not ZDR-eligible, charges $0.08/session-hour on top of tokens. Dead
  for this use case.
- **Adopting Agno**: its `ClaudeAgent` doesn't pass `session_store` (verified: 0
  occurrences) and maps sessions in an in-RAM `Dict` → loses `resume` on restart.
- **Adopting ArcReel**: AGPL-3.0 (viral) and its `DbSessionStore` is an internal lib,
  not a callable service.
- **Azure for the droplet**: the whole burstable B-series was blocked at subscription
  level (28 attempts, 7 regions). The daemon lives on DigitalOcean — budget law in
  [`.claude/rules/do-budget.md`](.claude/rules/do-budget.md).

## How to work here

- **English only.** Every byte committed to this repo is written in English — see
  [`.claude/rules/english-only.md`](.claude/rules/english-only.md).
- **The log is the truth.** Touching memory or rendering? Read
  [`.claude/rules/log-is-the-truth.md`](.claude/rules/log-is-the-truth.md) first.
- **Verify against the code, not the docs and not your memory.** This repo already
  produced three false claims that only source code disproved.
- **Bernard distinguishes learning from building.** When he is understanding something,
  don't rush ahead writing code: you would be stealing it from him. The droplet is
  deliberately his Linux curriculum — show the raw surface (SSH, `systemctl`,
  `journalctl`), don't wrap it away. Ask if it isn't obvious which mode is active.
- **What's built vs what's next**: the honest status table is in the
  [README](README.md#status--honest); the roadmap is
  [`.claude/backlog/`](.claude/backlog/README.md).
