# Genesis — the spirit, the blueprint, the science

Where AIRE's shape comes from. This is the story; the operating rules it
produced live in [`CLAUDE.md`](../CLAUDE.md) and
[`.claude/rules/log-is-the-truth.md`](../.claude/rules/log-is-the-truth.md).

## The spirit

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
| ***"oxygen, nitrogen and argon"*** | The three: **the memory** (Postgres), **the work** (artifacts, fetched by hand — no git, not yet), **the body** (the container, borrowed). |
| ***"I was passing, how curious, into the gaseous state"*** | The day this was born: it started as a VM —body, disk, SSH, IP— and kept deflating until no matter was left. |
| ***"this room is too small for the things I dream"*** | The original question was *"what's the difference between EC2 and an Azure VM?"*. The room was that question. |
| ***"I became human again. Don't miss the funeral."*** | **In the song, getting the body back is death.** Same here: **AIRE dies the day its memory depends on a body again** — on a disk that gets wiped after 30 days, on a machine that must be kept alive, on a database that belongs to someone else. |

**As long as it stays air —shapeless, in the owner's database, with no body to lose—
there is no funeral.** That is the litmus test for every design decision in this repo:

> *Does this give the agent a body back? Then no.*

That's why the ephemeral VM, the eternal VM, Managed Agents and the persistent disk all
died. They were all bodies.

## The blueprint — EC-GPS

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

AIRE is that machine piece by piece — the mapping table lives in the
[README](../README.md#where-the-shape-comes-from). The Perl parser turned a
fixed-format GPRS packet into a row with a regex; AIRE's turns a prompt into a session
that reasons. Same skeleton; the parsing step became intelligence. (EC-GPS never used
git either: when the service produced artifacts, they were downloaded by hand for
analysis. AIRE inherits that too — see decision #3 in `CLAUDE.md`.)

### What evolved from the blueprint — two things, not one

**1. The memory without a body.** EC-GPS's magic is **welded to a mortal body**: if
the droplet dies, `gps_logs` dies and the business dies with it. AIRE **rips the body
away from the memory** — `gps_logs` becomes Postgres, in the owner's database. Hence
*"no body to lose"*. Proven by the kill test (2026-07-13): the droplet was destroyed
and re-provisioned; the table never noticed — the old body's last line and the new
body's first sit on consecutive rows.

**2. The parser without a shape.** In EC-GPS the chassis was generic but the
generality **died in the parser**: the Perl knew exactly one thing, GPS packets. A new
domain (a POS, a sensor) meant writing a new parser — the transform always had a fixed
shape. What AIRE puts between the `accept()` and the `INSERT` is a transform that
already contains **every area of knowledge**: the same brain reasons over a biology
simulation, a market scan, or a GPS packet without a single new line of code. The
song's *"no defined shape"* goes one level deeper than plumbing — it is a **shapeless
mind**.

And that is why the **session casitas** (the `workspaces/{timestamp}_{uuid}_{name}`
folders the MKDIR verb creates) are architecture, not hygiene: a universal brain
without rooms would be a soup — one domain bleeding into another. The folder is the
domain boundary; each casita gets its own memory thread in Postgres
(`project_key`/`session_id`). One brain, one room per discipline: a **multifolder
mind**. Bernard's phrase *"my personal Mac, but in the cloud"* was more literal than
it sounded — the analogy was never the hardware, it was the **owner of the folders**.
On his Mac, the multifolder brain is him and `Documents` holds his casitas; on the
droplet, it is AIRE.

## The science — the log is the truth, the view is a cache

The waiter-vs-magic distinction **is not intuition: it is the central theorem of modern
data engineering.** Verified against canonical literature (some of it peer-reviewed):

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

The consequences for this repo are law, not commentary — they live in
[`.claude/rules/log-is-the-truth.md`](../.claude/rules/log-is-the-truth.md): the
append-only transcript in Postgres is the only truth; the front's views and the in-RAM pool
are derived caches; the engine is the listening daemon (Reactor / C10K) and AI is just
the *transform* between the `accept()` and the `INSERT`.
