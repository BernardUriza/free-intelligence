# AIRE

**A**rtificial **I**ntelligence **R**eflector **E**nvelope

> A daemon listening on a port, on an always-on Linux box you can SSH into and
> watch. The 25-year-old skeleton — with the parser turned into intelligence.

AIRE is being built in two layers, deliberately in this order:

1. **The chassis — running today on a DigitalOcean droplet.** A bare TCP daemon
   that accepts connections and appends every line to a greppable log. No AI in
   it, on purpose.
2. **The intelligence — in the repo, waking up next.** An HTTP server that wraps
   the [Claude Agent SDK](https://code.claude.com/docs/en/agent-sdk/overview),
   mirrors each session's memory into **your** Postgres, and speaks only
   events (SSE) — the daemon never returns HTML; every view lives in the
   front repo.

## What is breathing right now (the droplet)

An Ubuntu 24.04 droplet (`s-1vcpu-512mb`, ~$4/mo, `nyc3`) runs two systemd
units 24/7:

- **`aire-listener`** (`aire/listener.py`) — the daemon: `accept()` → read
  lines → append to `/opt/aire/aire.log`; with `AIRE_DATABASE_URL` set, each
  line is also mirrored to an append-only Postgres table (the pen).
- **`aire-device`** (`demo_device.py`) — a simulated GPS device: a `KEEPALIVE`
  heartbeat every ~2s, plus random `MESSAGE` events.

The whole point of this phase is the experience of watching a living daemon:

```bash
ssh -i ~/.ssh/aire_vm root@<IP> 'tail -f /opt/aire/aire.log | grep KEEPALIVE'
```

If the keep-alives are flowing, the air is still blowing (the `/soplo` ritual).
And the raw surface is deliberate — a droplet instead of a PaaS is also **the
Linux curriculum**: SSH, `systemctl`, `journalctl`, a port bound by a real
process. The friction is the value.

Deploys are **never done by hand**: every push to `main` touching the code makes
GitHub Actions SSH in, reset to `origin/main`, restart both units and verify
each one came back `active`. Runbooks: [`infra/`](infra/README.md)
(provisioning + the $20/mo budget law) and [`deploy/`](deploy/README.md)
(the CI/CD contract).

## Two doors to the same brain

The droplet answers to **two** kinds of caller, and they are not the same door:

| | **The SSH door** | **The AIRE door** |
|---|---|---|
| How | `ssh -t` + `tmux` + the `claude` CLI | `POST /projects/{p}/sessions/{s}/messages` (SSE) |
| Who | a human, in a terminal | your apps |
| Surface | the Claude Code TUI, live, remote | events; the front renders them |
| Memory | the droplet's disk (`~/.claude`) — **mortal** | Postgres, in the owner's database — **deathless** |
| Casita | `workspaces/<name>/` | `workspaces/<project>/` (same idea, engine-owned) |

**The SSH door** is the "my Mac, but in the cloud" experience: the real Claude
Code interface running in NYC, painted to your terminal. Long tasks must run
under **tmux** or they die with your laptop's SSH (the ritual and the `Ctrl-b`
collision are in the playbook's `long-running-remote-agent-tmux` rule):

```bash
ssh -t -i ~/.ssh/aire_vm root@<IP> \
  "tmux new -A -s libro 'cd /opt/aire/workspaces/libro && set -a; . /etc/aire/env; set +a; exec /root/.local/bin/claude'"
# Ctrl-q detaches (it keeps working); the same command re-attaches.
```

**Honest caveat — the SSH door is NOT deathless.** Its transcript lives on the
droplet's disk, so killing the box loses that conversation (the artifacts on
`workspaces/` too — fetch them by hand, EC-GPS style). Only sessions that come
in through the AIRE door mirror their memory to Postgres. Wiring the SSH door
into the same store is backlog #17.

## Where the shape comes from

EC-GPS: a GPS-tracking machine that has printed money for two decades with a
Perl daemon, an append-only table, and a console that only reads. AIRE is that
machine, piece by piece — full story in [`docs/genesis.md`](docs/genesis.md):

| EC-GPS | AIRE today | AIRE next |
|---|---|---|
| GPS receivers push over GPRS | demo device pushes over TCP | apps push prompts over HTTP |
| Perl daemon on a port | `aire/listener.py` on :9099 | the engine that owns the SDK |
| writes `gps_logs`, append-only | appends to `aire.log` (+ the pen → Postgres) | mirrors the transcript to Postgres |
| PHP console reads and displays | `ssh` + `grep` | aire-front (separate repo) paints it |

Same skeleton; the parsing step becomes reasoning. The log and the socket are
eternal — AI is just the *transform* (the repo's law:
[`log-is-the-truth`](.claude/rules/log-is-the-truth.md)).

## Where it's going: a substitute AND an enhancer of the Claude API

Your apps stop calling `api.anthropic.com` and call AIRE — same slot (an HTTP
endpoint, not a library), plus what the raw API will never give you:

- **`?mode=complete`** — the substitute: a bare turn, no tools.
- **`?mode=agent`** — the enhancer: a full Claude Code session that executes tools.
- **It remembers** (transcript mirrored to your Postgres, survives any container)
  and **lets itself be watched** — through the front repo, which renders the
  daemon's raw SSE events; the daemon itself never returns HTML.

First consumer: fi-runner (free-intelligence) calls AIRE over HTTP instead of
owning the SDK. Why nobody else fills this gap — the mirror, the broom, the
day-30 Blackwall, the competitive table — is in [`docs/thesis.md`](docs/thesis.md).

## Architecture

```
   your projects                AIRE                    the permanent
  ─────────────────      ──────────────────      ────────────────────────
   any language        ──►  POST /messages
                            Claude Agent SDK   ──►  transcript  →  Postgres
                            (disposable
                             container)        ──►  the work    →  artifacts,
                                                                   fetched by hand
```

- **The memory** — the transcript, in your Postgres. *The only irreplaceable
  piece: delete the container and AIRE lives on; delete the database and AIRE
  is dead.*
- **The work** — what the agent produces, on its workdir. **AIRE doesn't touch
  git** — like EC-GPS, artifacts are fetched by hand; at this level that IS the
  design (decision #3 in [`CLAUDE.md`](CLAUDE.md)).
- **The body** — the container. Born, works, dies, stores nothing. (The droplet
  is the body of the *chassis* phase; the memory never depends on its disk.)

Not a VM runner, not a library, not an SDK reimplementation — AIRE is the
missing glue around the SDK, callable from any language.

## Status — honest

| Layer | State |
|---|---|
| Droplet + listener + device + CI/CD + costwatch | ✅ **Live**, heartbeats accumulating 24/7 |
| The pen — log mirrored to Postgres | ✅ Live behind `AIRE_DATABASE_URL` |
| Postgres session store (`aire/store.py`) | ✅ SDK conformance suite green (local) |
| Engine + SSE events (`aire/engine.py`, `server.py`) | ✅ **Live** on the droplet :8088, Bearer-gated, budget-capped |
| The console — [`aire-front-seed`](https://github.com/BernardUriza/aire-front-seed), the read half | ✅ **Live** on Container Apps ([open it](https://aire-front.greendune-53f1f4af.eastus2.azurecontainerapps.io)) — tables, browse, SQL console, the monster. Behind HTTP Basic, reading as `aire_reader` (`GRANT SELECT` only) |
| **The tracer that proves the thesis** — chapter 1 → kill the process → chapter 2 remembers | ⏳ **Next** (backlog #5) |
| The broom (retention, backups, metrics) | Backlog |

Roadmap: [`.claude/backlog/`](.claude/backlog/README.md). Agent context:
[`CLAUDE.md`](CLAUDE.md). Story and pitch: [`docs/`](docs/).

## License

To be defined.
