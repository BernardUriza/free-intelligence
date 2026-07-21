# AIRE

**A**rtificial **I**ntelligence **R**eflector **E**nvelope

> A daemon listening on a port, on an always-on Linux box you can SSH into and
> watch. The 25-year-old skeleton — with the parser turned into intelligence.

AIRE is being built in two layers, deliberately in this order:

1. **The chassis — running today on a DigitalOcean droplet.** A bare TCP daemon
   that accepts connections and appends every line to a greppable log. No AI in
   it, on purpose.
2. **The intelligence — awake since 2026-07-20.** An HTTP server that wraps
   the [Claude Agent SDK](https://code.claude.com/docs/en/agent-sdk/overview),
   mirrors each session's memory into **your** Postgres, and speaks only
   events (SSE) — the daemon never returns HTML; every view lives in the
   front repo.

## What is breathing right now (the droplet)

An Ubuntu 24.04 droplet (`s-1vcpu-512mb`, ~$4/mo, `nyc3`) runs these systemd
units 24/7:

- **`aire-listener`** (`server/aire/listener.py`) — the daemon: `accept()` → read
  lines → append to `/opt/aire/aire.log`; with `AIRE_DATABASE_URL` set, each
  line is also mirrored to an append-only Postgres table (the pen). The `MKDIR`
  verb (token-gated) creates session casitas.
- **`aire-server`** (`aire/server.py`) — the engine's HTTP surface on :8088:
  SSE events only, Bearer-gated, budget-capped.
- **`aire-sweep.timer`** — the broom (30-day retention).
- **`aire-device`** (`demo_device.py`) — the simulated GPS device that pushed
  `KEEPALIVE` heartbeats. **Retired 2026-07-14**: it proved the chassis (24k
  heartbeats, the kill test, the first casitas) and its job is done. The unit is
  installed but `disabled`; `systemctl start aire-device` brings it back for a
  demo. Real events (web `VISIT` beacons, `MKDIR` verbs) feed the log now.

The whole point of this phase is the experience of watching a living daemon:

```bash
ssh -i ~/.ssh/aire_vm root@<IP> 'tail -f /opt/aire/aire.log'
```

If the daemon answers and the pen still writes, the air is still blowing (the
`/soplo` ritual).
And the raw surface is deliberate — a droplet instead of a PaaS is also **the
Linux curriculum**: SSH, `systemctl`, `journalctl`, a port bound by a real
process. The friction is the value.

Deploys are **never done by hand**: every push to `main` touching the code makes
GitHub Actions SSH in, reset to `origin/main`, restart the units and verify
each one came back `active`. Runbooks: [`infra/`](infra/README.md)
(provisioning + the $20/mo budget law) and [`deploy/`](deploy/README.md)
(the CI/CD contract).

## Two doors to the same brain

The droplet answers to **two** kinds of caller, and they are not the same door:

| | **The SSH door** | **The AIRE door** |
|---|---|---|
| How | `ssh -t` + `tmux` + the `claude` CLI | `POST /projects/{p}/sessions/{s}/messages` (SSE) |
| Who | **a human, in a terminal — only** | your apps, and every agent |
| Surface | the Claude Code TUI, live, remote | events; the front renders them |
| Memory | the disk, mirrored every minute → **deathless** | Postgres, written directly → **deathless** |
| Casita | `workspaces/{ts}_{uuid}_{name}/` (MKDIR) | `workspaces/<project>/`, or an existing casita by name |

**One memory, two doors** (2026-07-20). The SSH door's transcript is no longer
mortal: `mirror.py` carries it to `claude_session_store` every minute and
`restore.py` re-materializes it on a fresh box (backlog #17). And the AIRE door
can now **continue a session the CLI started** — a session name that already is
a UUID is honoured verbatim, and a project may name an existing casita, so the
`project_key` lands exactly where the CLI wrote. Verified live: a session born
in tmux answered over HTTP with its full memory.

**An agent NEVER drives the daemon through SSH.** Reaching for SSH is the tell
of a missing endpoint — build the endpoint and use it
([`.claude/rules/ssh-is-a-missing-endpoint.md`](.claude/rules/ssh-is-a-missing-endpoint.md)).
SSH may operate the body; it is Bernard's own terminal, not an agent's API.

**The SSH door** is the "my Mac, but in the cloud" experience: the real Claude
Code interface running in NYC, painted to your terminal. Long tasks must run
under **tmux** or they die with your laptop's SSH (the ritual and the `Ctrl-b`
collision are in the playbook's `long-running-remote-agent-tmux` rule):

```bash
ssh -t -i ~/.ssh/aire_vm root@<IP> \
  "tmux new -A -s libro 'cd /opt/aire/workspaces/libro && set -a; . /etc/aire/env; set +a; exec /root/.local/bin/claude'"
# Ctrl-q detaches (it keeps working); the same command re-attaches.
```

**Honest caveat — the ARTIFACTS are still mortal.** The transcript survives the
box, but what the agent WRITES lives on `workspaces/` and dies with the droplet:
fetch it by hand, EC-GPS style (decision #3). Proven the hard way on 2026-07-20 —
a re-provisioned droplet came back with the ants book's folder empty; the session
resumed from Postgres, rebuilt volume 1 from its own memory, and then wrote
volume 2.

## Where the shape comes from

EC-GPS: a GPS-tracking machine that has printed money for two decades with a
Perl daemon, an append-only table, and a console that only reads. AIRE is that
machine, piece by piece — full story in [`server/docs/genesis.md`](server/docs/genesis.md):

| EC-GPS | AIRE today (every row landed 2026-07-20) |
|---|---|
| GPS receivers push over GPRS | apps push prompts over HTTP (:8088), devices push lines over TCP (:9099) |
| Perl daemon on a port | `server/aire/listener.py` + the engine that owns the SDK |
| writes `gps_logs`, append-only | appends to `aire.log` AND mirrors the transcript to Postgres |
| PHP console reads and displays | `front/` paints it (`/claude`: folder → session → transcript) |

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
day-30 Blackwall, the competitive table — is in [`server/docs/thesis.md`](server/docs/thesis.md).

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
| Droplet + listener + CI/CD + costwatch + broom | ✅ **Live** 24/7 (the demo device is retired — it proved the chassis) |
| The pen — log mirrored to Postgres | ✅ Live behind `AIRE_DATABASE_URL` |
| Postgres session store (`aire/store.py`) | ✅ SDK conformance suite green (local) |
| Engine + SSE events (`aire/engine/`, `server.py`) | ✅ **Live** on the droplet :8088, Bearer-gated. `mode=agent` writes real files (fixed 2026-07-20: `bypassPermissions` is refused as root and had killed every agent turn) |
| The console — `front/`, the read half of this monorepo | ✅ **Live** on Container Apps ([open it](https://aire-front.greendune-53f1f4af.eastus2.azurecontainerapps.io)) — tables, browse, SQL console, the monster, and `/claude` (folder → session → transcript). Behind HTTP Basic, reading as `aire_reader` (`GRANT SELECT` only) |
| **The tracer that proves the thesis** — write → kill the box → remember | ✅ **Done 2026-07-20** (backlog #5), and not simulated: the droplet was re-provisioned, `workspaces/` came back EMPTY, and the resumed session rebuilt volume 1 of the ants book from its Postgres memory before writing volume 2. Two books now live in the store, both readable at `/claude` |
| The broom (retention, backups, metrics) | Retention live (sweep + logrotate + the /tmp broom); **DB backups live via Azure** (7-day point-in-time restore, verified 2026-07-20); metrics partial (weight on `/claude`; cost needs persistence) |
| The budget ceiling | ✅ A cut turn now emits a real `budget_exhausted` error and retires its spent client (fixed + verified 2026-07-20). Open: at $1.00 a long agent job still needs batching — Bernard's spend call (backlog #23) |

Roadmap: [`.claude/backlog/`](.claude/backlog/README.md). Agent context:
[`CLAUDE.md`](CLAUDE.md). Story and pitch: [`docs/`](docs/).

## License

To be defined.
