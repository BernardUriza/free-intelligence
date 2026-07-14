# AIRE — context for agents

**A**rtificial **I**ntelligence **R**eflector **E**nvelope. An HTTP server that wraps
the Claude Agent SDK and mirrors each session's transcript to Postgres.

---

## The spirit (read this before the facts)

> *Air,*
> *for a moment I dreamed I was*
> *air: oxygen, nitrogen and argon,*
> ***with no defined shape and no color.***
> *I was flying air.*
>
> — Mecano, "Aire" (J. M. Cano, 1984; translated from the Spanish)

The acronym came later. **The name already existed, and it was better.** The 1984 song
turned out to be the project's specification, and not by chance — because it describes
exactly what we discovered:

| The song | The architecture |
|---|---|
| ***"with no defined shape and no color"*** | The container **stores nothing**. The bodiless agent. It's the tagline. |
| ***"oxygen, nitrogen and argon"*** | The three: **the memory** (Postgres), **the work** (git), **the body** (the container, borrowed). |
| ***"I was passing, how curious, into the gaseous state"*** | The day this was born: it started as a VM —body, disk, SSH, IP— and kept deflating until no matter was left. |
| ***"this room is too small for the things I dream"*** | The original question was *"what's the difference between EC2 and an Azure VM?"*. The room was that question. |
| ***"I became human again. Don't miss the funeral."*** | **In the song, getting the body back is death.** Same here: **AIRE dies the day its memory depends on a body again** — on a disk that gets wiped after 30 days, on a machine that must be kept alive, on a database that belongs to someone else. |

**As long as it stays air —shapeless, in the owner's database, with no body to lose—
there is no funeral.** That is the litmus test for every design decision in this repo:

> *Does this give the agent a body back? Then no.*

That's why the ephemeral VM, the eternal VM, Managed Agents and the persistent disk all
died. They were all bodies.

## The genesis — where the shape came from (it wasn't invented here)

The original question —*"what's the difference between an EC2 and a VM?"*— had an answer
Bernard had already seen working years earlier, at a GPS-tracking company: **EC-GPS**
(`ec-gps.com`, run by Carlos Feria Tapia, Zapopan). Its entire revenue machine, to this
day, is this:

- The **GPS receivers push** their position over **GPRS** to an always-on server.
- That server —*"the management center"*— is a **Perl daemon** listening on a few ports,
  living on a **Linux VM in a droplet**, maintained over **SSH**.
- The daemon **parses** each packet and **writes it to an append-only table, `gps_logs`.**
- The **PHP** backend (`/app`, the console) is **the waiter**: it only **reads** `gps_logs`
  and shows it on a map. It never writes it. It is replaceable (GoDaddy, Vercel, doesn't
  matter).

That is the answer to EC2-vs-VM: for a listening daemon, **an EC2 and a VM in a droplet
are the same thing** — an always-on Linux body with an open port and SSH. You don't need
AWS's elegance; you need a body that doesn't shut down.

**AIRE is that machine, piece by piece** — not an analogy, the literal blueprint:

| EC-GPS (Carlos FT's machine) | AIRE |
|---|---|
| GPS receivers push over GPRS | apps push prompts over HTTP |
| **Perl** daemon listening on a port | the **engine** that owns the SDK (`aire/engine.py`) |
| parses and writes `gps_logs` (append-only) | mirrors the transcript to the `session_store` (append-only, Postgres) |
| the **PHP waiter** reads and displays | the **SSR** reads and paints it for you, live |
| Linux VM in a droplet, SSH | the always-on server |

The Perl parser turned a fixed-format GPRS packet into a row with a regex. **AIRE's
turns a prompt into a session that reasons.** Same skeleton; the parsing step became
intelligence. And the only evolution over EC-GPS: its magic is **welded to a mortal
body** (if the droplet dies, `gps_logs` dies and the business dies with it); AIRE
**rips the body away from the memory** — `gps_logs` becomes Postgres, in the owner's
database. Hence *"no body to lose"*.

## The waiter and the magic — the log is the truth, the view is a cache (scientific backing)

The waiter-vs-magic distinction **is not intuition: it is the central theorem of modern
data engineering.** Verified against canonical literature (some of it peer-reviewed) by
`/histerical-search`:

- **Jay Kreps, "The Log"** (creator of Kafka, LinkedIn Eng): *the log is the simplest
  possible storage abstraction —append-only, totally ordered by time—* and **the table
  is a cache / derived view of the log.** You don't understand databases, replication,
  consensus or version control without understanding it.
  <https://engineering.linkedin.com/distributed-systems/log-what-every-software-engineer-should-know-about-real-time-datas-unifying>
- **Pat Helland, "Immutability Changes Everything"** (ACM Queue / CIDR 2015):
  *"accountants don't use erasers"* — everything is append-only, and **"the contents of
  the database are a caching of the latest values in the logs."**
  <https://queue.acm.org/detail.cfm?id=2884038>
- **WAL / ARIES** (implemented by Postgres, Oracle, MySQL): durability is achieved by
  writing first to a sequential **append-only log** — faster than random access.
- **Martin Fowler, Event Sourcing**: the **append-only event store is the single source
  of truth**; state is a derived view. Canonical example: version control (the commit
  log is the truth; the working copy is derived).
  <https://martinfowler.com/articles/201701-event-driven.html>

**Hard consequence for this repo** (it is `[[log-is-the-truth]]`, the repo's law):

- The **`session_store` (append-only transcript in Postgres) is THE TRUTH** — the magic.
  The **SSR / `render.py` is the derived view** — the waiter. That's why *kill the
  process → `GET` → repaint from Postgres* works: it is event sourcing (rebuilding state
  by reprocessing the log), not a trick.
- **NEVER** let the rendered view, the in-RAM pool, or any cache become the source of
  truth. The append-only transcript is the only truth; everything else derives from it.
- The **engine is the listening daemon** (Reactor pattern / event loop, the C10K problem
  of 1999). The only new thing between the `accept()` and the `INSERT` is that the
  parser now reasons. AI is the *transform*; the log and the socket are eternal and
  untouchable.

---

Everything below was **verified against the source code of the installed SDK**
(`claude-agent-sdk` 0.2.116) or the official docs — never against memory. If you're
going to contradict anything here, verify it first the same way.

## The decisions, already made

1. **AIRE is a SERVICE, not a library.** You don't import it: you call it over HTTP.
   That way the SDK lives in a single place, the Postgres credentials live in a single
   place, and any language can talk to it.
0. **THE SERVER IS THE INTERFACE — SSR, not a JSON API.** This is the central thesis and
   what separates AIRE from everything else. The others expose the SDK as an API and
   leave the frontend to you (agent-webkit = React hooks; the cookbook = JSON over SSE).
   AIRE **returns server-rendered HTML that keeps writing itself** as the agent thinks.
   `GET /projects/avatar` → a page, with the agent working, live. No React, no npm, no
   build, no frontend.
   - Free consequence: the "page to view my sessions" **is not another project** — it's
     the same server.
   - Real technical challenge: an agent doesn't answer within one request (it thinks,
     uses tools, corrects itself). This needs **streaming HTML**: the page arrives
     immediately and the SDK's events keep painting it. It is not classic one-shot SSR.
   - That's why none of the six repos surveyed would do: they're all API-first.
2. **One database, one `project_key` per project.** The SDK's `SessionKey` already
   carries `project_key`; its docstring says *"Multi-tenant deployments should set this."*
3. **The memory (transcript) goes to Postgres. The work (the files) goes to git.**
   Separated on purpose.
4. **The container stores nothing.** `CLAUDE_CONFIG_DIR=/tmp`.

## What NOT to write — it already exists

- **The Postgres store**: `examples/session_stores/postgres_session_store.py` in
  [claude-agent-sdk-python](https://github.com/anthropics/claude-agent-sdk-python).
  Uses asyncpg, PK `(project_key, session_id, subpath, seq)`. **Copy it, don't write it.**
  (That mistake was already made once: a store that already existed got written by hand.)
- **The HTTP server**: `claude_agent_sdk/hosting/` in
  [claude-cookbooks](https://github.com/anthropics/claude-cookbooks) — FastAPI + SSE +
  `POST /sessions/{id}/messages` + Dockerfile + K8s + Modal.
- **The conformance suite**: `from claude_agent_sdk.testing import run_session_store_conformance`
  — 14 contracts, ships inside the package. Run it against any store.

## The HTTP contract

What the official server (`claude-cookbooks/hosting/server.py`) **already exposes**,
verified by reading its code:

```http
GET  /health
POST /sessions/{session_id}/messages
     Authorization: Bearer <AGENT_AUTH_TOKEN>    # it does have auth: _require_token + compare_digest
     { "prompt": "..." }
     → text/event-stream  (event: message … event: done)
```

What **AIRE** exposes, opening the axis the cookbook lacks (it has `cwd="/app"`
hardcoded → a single project):

```http
POST /projects/{project}/sessions/{session}/messages
```

Maps 1:1 to the SDK's `SessionKey`: `{project_key, session_id}`. The SDK requires
`session_id` to be a **UUID** (it validates it), but it **does let you set it** → derive
it deterministically from the name with `uuid5(NS, "avatar/manuscript")`: readable names
outside, UUIDs inside, no mapping table.

## What DOES need writing (~150 lines)

It's what the official cookbook does **not** ship:

1. Wire `session_store=` into the `ClaudeAgentOptions` (the cookbook doesn't: look at
   its `_build_options()`).
2. `project_id` → `cwd` + `CLAUDE_CONFIG_DIR` per project (it has `cwd="/app"` hardcoded).
3. Multi-tenant isolation: `setting_sources=[]`, `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`.
4. Handle the `mirror_error` event and deduplicate by `entry.uuid` in `append()`.
5. Drop its `_remember()` / `hosting_session_map.json` (the in-RAM dict): with a
   settable `session_id` + `uuid5`, no mapping is needed at all.

## Verified SDK facts (don't re-discover them)

- **`session_id` CAN be set.** `subprocess_cli.py:355` → `cmd.extend(["--session-id", ...])`.
  **No mapping table needed** from external id to SDK id.
- **`session_store` and `enable_file_checkpointing` are INCOMPATIBLE.** The SDK raises
  `ValueError` (`session_store_validation.py`): *"checkpoints are local-disk only and
  would diverge from the mirrored transcript."* → **Scratch-vs-permanent is solved with
  git (branches, `git mv`), not with `rewind_files()`.**
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
- **`Stop` hook** → that's where the `git commit && push` goes when each job closes.
- **`max_budget_usd`** → hard spend cap per query.

## Discarded routes (don't re-propose them)

- **Ephemeral VM with SSH** (the original `air-lite`): it's the Agent SDK reinvented
  with `boto3` + `paramiko`. Dead.
- **Persistent VM ("never terminate")**: reinvents git as storage and pays 24/7 rent for
  a disk that is a single point of failure. Dead.
- **Managed Agents** (Anthropic's hosted offering): the memory lives **on their side**,
  no `session_store`, not eligible for ZDR, and it charges **$0.08 per session-hour** on
  top of tokens. Kills the dashboard and your own queries. Dead for this use case.
- **Adopting Agno AgentOS**: its `ClaudeAgent` **does not pass `session_store`**
  (0 occurrences in its code) and keeps the mapping in an in-RAM `Dict` → loses `resume`
  on restart. Verified by reading `libs/agno/agno/agents/claude/agent.py`. It has the
  same hole AIRE exists to plug.
- **Adopting ArcReel**: it's **AGPL-3.0** (viral) and its `DbSessionStore` is an internal
  library of their product, not a service. It can't be called from other projects.

## The state of the art (verified by reading code, July 2026)

**It is NOT true that "nobody wires the `session_store`"** — that claim was in this file
and it was **false**. The truth, by axis:

| | Mirrors to a DB | Reusable HTTP server | Housekeeping |
|---|---|---|---|
| `claude-cookbooks/hosting` (official) | ❌ in-RAM dict + disk | ⚠️ single project (`cwd="/app"`) | ❌ |
| Agno (41k ⭐) | ❌ in-RAM dict + disk | ✅ | ❌ |
| [ArcReel](https://github.com/ArcReel/ArcReel) (3.2k ⭐, AGPL) | ✅ `DbSessionStore`, SQLAlchemy (PG/SQLite) | ❌ internal lib | ❌ |
| **AIRE** | ✅ | ✅ | ✅ |

ArcReel is proof the use case is real: their product is novel → characters → scenes →
video, and they arrived at the same solution. But **none of the three sweeps**: zero
`ttl`/`retention`/`cleanup`/`archive` in their code.

## Housekeeping is a pillar, not an extra

The `SessionStore` docstring **delegates retention to the adapter, in writing**:

> *"The SDK **never deletes** from your store… Retention is the adapter's responsibility —
> implement TTL, object-storage lifecycle policies, or scheduled cleanup according to your
> compliance requirements (e.g. ZDR/HIPAA retention windows)."*

That is: the memory **accumulates forever** by design, and cleaning it is the adapter's
job. Nobody has done it. That is AIRE's cleanest gap.

## How to work here

- **English only.** Every byte committed to this repo is written in English — see
  `.claude/rules/english-only.md`.
- **Verify against the code, not the docs and not your memory.** One session produced
  three false claims that only the source code disproved.
- **Bernard distinguishes learning from building.** When he is understanding something,
  don't rush ahead writing code: you would be stealing it from him. Ask if it isn't
  obvious which of the two modes is active.
