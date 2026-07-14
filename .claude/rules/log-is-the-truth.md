# The log is the truth, the view is a cache (AIRE's law)

Repo rule for `aire-server`. Instantiates the genesis and the scientific backing in
`CLAUDE.md` (the *"The waiter and the magic"* section). If you're touching AIRE's
memory or its rendering, this law rules.

## The theorem

The **append-only transcript** the `session_store` mirrors to Postgres is **THE ONLY
SOURCE OF TRUTH**. Everything else —the SSR view, the in-RAM client pool, any cache—
is **derived from the log**, never the other way around. This is not a design opinion:
it is the consensus of modern data engineering.

- **Jay Kreps, "The Log"** (creator of Kafka): the log is the simplest possible storage
  abstraction —append-only, totally ordered— and **the table is a cache / derived view
  of the log**.
  <https://engineering.linkedin.com/distributed-systems/log-what-every-software-engineer-should-know-about-real-time-datas-unifying>
- **Pat Helland, "Immutability Changes Everything"** (ACM Queue / CIDR 2015):
  *"accountants don't use erasers"*; **"the contents of the database are a caching of
  the latest values in the logs."**
  <https://queue.acm.org/detail.cfm?id=2884038>
- **WAL / ARIES** (Postgres, Oracle, MySQL): durability is founded on a sequential
  append-only log.
- **Martin Fowler, Event Sourcing**: the append-only event store is the single source
  of truth; state is a derived view (canonical example: version control).
  <https://martinfowler.com/articles/201701-event-driven.html>

## The genesis (why this shape, and no other)

AIRE is, piece by piece, the **EC-GPS** machine (Carlos Feria Tapia): GPS receivers
pushing over GPRS → a **Perl daemon** listening on a port → writing `gps_logs`
(append-only) → a **PHP waiter** that only reads it and displays it. AIRE is the same
thing with the parser turned into intelligence:

- **The engine (`aire/engine.py`) is the listening daemon** — Reactor pattern / event
  loop (the C10K problem, 1999). The listening socket is eternal; the only new thing
  between the `accept()` and the `INSERT` is that the parser now reasons. **AI is the
  *transform*, not the chassis.**
- **`gps_logs` = the `session_store`.** The append-only table in Postgres.
- **The PHP waiter = `render.py` / the SSR.** Reads the log and paints it. Replaceable.

## Prohibitions (what this law forbids)

1. **NEVER make the view or a cache the source of truth.** The in-RAM
   `ClaudeSDKClient` pool is a **hot cache, not truth**: a miss is rebuilt from the
   store with `resume=`. If the process dies, the truth stays in Postgres. *Kill the
   process → `GET` → repaint from the store* must always work; the day it stops
   working, you broke the law.
2. **NEVER move the memory into a mortal body.** That is AIRE's only evolution over
   EC-GPS: Carlos FT's magic is welded to his droplet (if it dies, `gps_logs` dies).
   AIRE's memory lives in the **owner's** database, decoupled from the process that
   writes it. A transcript on the VM's disk, in a local checkpoint, or in a dict that
   never gets persisted **gives the agent a body back** — and by the litmus test in
   `CLAUDE.md`, that is death.
3. **The transcript is append-only; never mutate it.** Retention (housekeeping) is done
   with `DELETE ... WHERE mtime < cutoff` as adapter policy, never by rewriting
   entries. To correct is to append, not to erase (Helland).

See also `CLAUDE.md` (sections *"The spirit"*, *"The genesis"*, *"The waiter and the
magic"*) and `aire/store.py` (the official Postgres adapter, copied).
