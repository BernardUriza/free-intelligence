# AIRE

**A**rtificial **I**ntelligence **R**eflector **E**nvelope

> Claude Code, exposed as a web page. No frontend. And it never forgets a thing.

A server that wraps the [Claude Agent SDK](https://code.claude.com/docs/en/agent-sdk/overview),
**mirrors** each session's memory into **your** database, and **renders the agent
working — on the server.**

You hit it with a browser and there's Claude, writing. You never built a UI.

## The thesis: the server IS the interface

Everyone else exposes the SDK as an **API** and leaves the frontend to you
(agent-webkit gives you React hooks; the cookbook gives you JSON over SSE). AIRE does
the opposite: **it returns HTML, rendered on the server, that keeps writing itself**
as the agent thinks.

```
GET /projects/avatar
→ a page. With the agent working. Live.
```

No React. No npm. No build. No frontend. It's what you see in your terminal when you
use Claude Code — but in a browser, without having written a single line of client code.

And as a free consequence: the page where you view your sessions **is not another
project**. It's the same server. The memory is yours, the table is yours, the HTML is
yours.

## And the broom

The SDK **never deletes** from your store, and Claude Code **does delete from its own**:
after 30 days, silently, with no warning and no recovery
([#59248](https://github.com/anthropics/claude-code/issues/59248) 👍13,
[#62476](https://github.com/anthropics/claude-code/issues/62476) 👍11,
[#61952](https://github.com/anthropics/claude-code/issues/61952): *"two months of work
I paid for, gone"*).

It's a **Blackwall**: a wall at day 30, and nothing remains on the other side.

> **It's your garbage, and you decide when it goes out.**

Retention you control. Sessions you can pin. Archiving instead of destruction.
Backups. Nobody serves this: not Anthropic, not claude-mem (86k ⭐), not mem0, not Letta.

```http
POST /projects/avatar/sessions/manuscript/messages
Authorization: Bearer <token>

{ "prompt": "write chapter 2" }
```

It answers with an SSE stream, event by event. And chapter 2 remembers chapter 1 —
even if the container that wrote chapter 1 has been dead for three days.

From a cron, from TypeScript, from a button, from your phone. Nobody needs Python,
or to know the SDK exists.

## The name is the architecture

| | |
|---|---|
| **Reflector** | The SDK calls its persistence hook a *mirror*: it reflects the transcript to an external store. AIRE is that mirror, pointed at your Postgres. |
| **Envelope** | The HTTP envelope that contains the agent. You don't import it: **you talk to it**. |

## The gap it fills

The Agent SDK's `SessionStore` is the official hook for getting the memory off disk
and into a database. And the SDK **never deletes from your store** — its docstring
delegates the cleanup to you in writing:

> *"Retention is the adapter's responsibility — implement TTL, object-storage lifecycle
> policies, or scheduled cleanup according to your compliance requirements."*

In other words: **two** things are needed. The **mirror** and the **broom**. Nobody
has both.

| | Mirrors to a DB | Reusable HTTP server | Housekeeping |
|---|---|---|---|
| [`claude-cookbooks/hosting`](https://github.com/anthropics/claude-cookbooks/tree/main/claude_agent_sdk/hosting) (official) | ❌ in-RAM dict + disk | ⚠️ single project (`cwd="/app"`) | ❌ |
| [Agno](https://github.com/agno-agi/agno) (41k ⭐) | ❌ in-RAM dict + disk | ✅ | ❌ |
| [ArcReel](https://github.com/ArcReel/ArcReel) (3.2k ⭐, AGPL) | ✅ Postgres/SQLite | ❌ internal lib of their app | ❌ |
| **AIRE** | ✅ | ✅ | ✅ |

Verified **by reading their code**, not their documentation:

- The cookbook and Agno keep the session mapping in an in-RAM `dict` and the transcript
  on **local disk** → they lose the memory when the container dies.
- ArcReel **does** wire the `SessionStore` (`DbSessionStore`, SQLAlchemy) — but it's an
  internal library of their product, under **AGPL**, not a service you can talk to from
  other projects.
- **None of the three sweeps.** Zero `ttl`, zero `retention`, zero `cleanup`, zero
  archiving. They accumulate forever.

AIRE is the mirror **and** the broom, behind an HTTP endpoint anyone can call.

## What it is NOT

- **Not a VM runner.** The container stores nothing, so it doesn't need to survive.
- **Not a library.** You don't import it; you call it over HTTP from any language.
- **It doesn't reimplement the SDK.** The agentic loop, the tools, the subagents, the
  permissions and the sandbox already belong to the SDK. AIRE is the missing glue.

## Architecture

```
   your projects                AIRE                    the permanent
  ─────────────────      ──────────────────      ────────────────────────
   any language        ──►  POST /messages
                            Claude Agent SDK   ──►  transcript  →  Postgres
                            (disposable
                             container)        ──►  the work    →  git
```

Three things, and only one of them is AIRE:

- **The memory** — the transcript, in your Postgres. *The only irreplaceable piece:
  delete the container and AIRE lives on; delete the database and AIRE is dead.*
- **The work** — what the agent produces, in git. Separate on purpose.
- **The body** — the container. It's born, it works, it dies. It stores nothing
  because that's not its job.

## It's your garbage

The SDK never deletes: **memory accumulates forever.** That's not a defect — it's what
keeps you from losing context. But someone has to sweep, and that someone is you (the
SDK says so explicitly).

And since the garbage is **yours**, living in **your** database, you can do anything
with it:

- **Retention** — per-project TTL, archive cold sessions, purge what's useless.
- **Scheduled backups** — it's Postgres. It's `pg_dump` and a cron job.
- **Auditing** — what you asked, what it did, what it cost. It's a `SELECT`.
- **A page to see it all** — because the table is yours.

None of this is possible when the memory lives on the provider's side.

## Status

The skeleton is in the repo — the bare TCP listener + demo device (the tracer), and
the engine / server / SSR / Postgres store. What's missing is tracked in
[`.claude/backlog/`](.claude/backlog/).

## License

To be defined.
