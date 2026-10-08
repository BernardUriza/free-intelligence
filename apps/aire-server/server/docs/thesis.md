# Thesis — why AIRE deserves to exist

The pitch behind the [README](../README.md)'s short version: what gap AIRE fills,
with receipts. Everything here was verified by reading the competitors' code, not
their docs.

## Why the memory MUST leave the process

In AIRE's very first live session, the agent answered on the streaming page, reported
its cost — and a page reload **erased the conversation**. Gone. That is the exact
failure this project exists to kill, and it's also what Claude Code does to everyone
at day 30: transcripts deleted silently, no warning, no recovery
([#59248](https://github.com/anthropics/claude-code/issues/59248) 👍13,
[#62476](https://github.com/anthropics/claude-code/issues/62476) 👍11,
[#61952](https://github.com/anthropics/claude-code/issues/61952): *"two months of work
I paid for, gone"*). A Blackwall: a wall at day 30, and nothing remains on the other
side.

> **It's your garbage, and you decide when it goes out.**

## The mirror and the broom

The Agent SDK's `SessionStore` is the official hook for getting the memory off disk
and into a database. And the SDK **never deletes from your store** — its docstring
delegates the cleanup to you in writing:

> *"The SDK never deletes from your store… Retention is the adapter's responsibility —
> implement TTL, object-storage lifecycle policies, or scheduled cleanup according to
> your compliance requirements (e.g. ZDR/HIPAA retention windows)."*

That is: the memory **accumulates forever** by design, and sweeping it is the
adapter's job. So two things are needed — the **mirror** and the **broom** — and
nobody has both:

| | Mirrors to a DB | Reusable HTTP server | Housekeeping |
|---|---|---|---|
| [`claude-cookbooks/hosting`](https://github.com/anthropics/claude-cookbooks/tree/main/claude_agent_sdk/hosting) (official) | ❌ in-RAM dict + disk | ⚠️ single project (`cwd="/app"`) | ❌ |
| [Agno](https://github.com/agno-agi/agno) (41k ⭐) | ❌ in-RAM dict + disk | ✅ | ❌ |
| [ArcReel](https://github.com/ArcReel/ArcReel) (3.2k ⭐, AGPL) | ✅ `DbSessionStore`, SQLAlchemy | ❌ internal lib of their app | ❌ |
| **AIRE** | ✅ | ✅ | ✅ |

- The cookbook and Agno keep the session mapping in an in-RAM `dict` and the transcript
  on **local disk** → they lose the memory when the container dies.
- ArcReel **does** wire the `SessionStore` — but it's an internal library of their
  product, under **AGPL**, not a service you can call from other projects. (It's also
  proof the use case is real: novel → characters → scenes → video, and they arrived at
  the same solution.)
- **None of the three sweeps.** Zero `ttl`, zero `retention`, zero `cleanup`, zero
  archiving. Housekeeping is a pillar of AIRE, not an extra — it is the cleanest gap.

## And since the garbage is yours, in your database

- **Retention** — per-project TTL, archive cold sessions, purge what's useless.
- **Scheduled backups** — it's Postgres. It's `pg_dump` and a cron job.
- **Auditing** — what you asked, what it did, what it cost. It's a `SELECT`.
- **A page to see it all** — because the table is yours.

None of this is possible when the memory lives on the provider's side.
