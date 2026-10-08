# The log is the truth, the view is a cache (AIRE's law)

Repo rule for `aire-server`. Instantiates the genesis and the scientific backing in
`CLAUDE.md` (the *"The waiter and the magic"* section). If you're touching AIRE's
memory or its rendering, this law rules.

## The theorem

The **append-only transcript** the `session_store` mirrors to Postgres is **THE ONLY
SOURCE OF TRUTH**. Everything else —the SSR view, the in-RAM client pool, any cache—
is **derived from the log**, never the other way around. This is not a design opinion:
it is the consensus of modern data engineering (Kreps's "The Log", Helland's
*"accountants don't use erasers"*, WAL/ARIES, Fowler's event sourcing — citations and
the EC-GPS genesis in [`server/docs/genesis.md`](../../server/docs/genesis.md)).

The mapping that follows from it: the engine (`server/aire/engine/`) is the listening
daemon (Reactor / C10K — the socket is eternal, AI is only the *transform*);
`gps_logs` = the `session_store`; the PHP waiter = `render.py` / the SSR, which only
reads and repaints. Replaceable.

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
magic"*) and `server/aire/store.py` (the official Postgres adapter, copied).
