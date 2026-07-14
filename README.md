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
   mirrors each session's memory into **your** Postgres, and renders the agent
   working — on the server.

## What is breathing right now (the droplet)

An Ubuntu 24.04 droplet (`s-1vcpu-512mb`, ~$4/mo, `nyc3`) runs two systemd
units 24/7:

- **`aire-listener`** (`aire/listener.py`) — the daemon: `accept()` → read
  lines → append to `/opt/aire/aire.log`, append-only, with timestamp and peer.
- **`aire-device`** (`demo_device.py`) — a simulated GPS device: a `KEEPALIVE`
  heartbeat every ~2s, plus random `MESSAGE` events (position, speed, panic,
  geofence).

The whole point of this phase is the experience of watching a living daemon:

```bash
ssh -i ~/.ssh/aire_vm root@<IP> 'tail -f /opt/aire/aire.log | grep KEEPALIVE'
```

If the keep-alives are flowing, the air is still blowing. That heartbeat check
is a ritual here (the `/soplo` command).

And the raw surface is deliberate. A droplet — not a PaaS, not serverless — is
also **the Linux curriculum**: SSH, `systemctl`, `journalctl`, the FHS
(`/opt/aire`), a port bound by a real process. The managed paths hide the OS;
this project chose the one path where you're forced to meet it. The friction is
the value.

Deploys are **never done by hand**: every push to `main` that touches the code
makes GitHub Actions SSH into the droplet, `git reset --hard origin/main`,
restart both units and verify **each one individually** came back `active` —
a dead unit breaks the job. See [`infra/`](infra/README.md) (provisioning,
one-time) and [`deploy/`](deploy/README.md) (the CI/CD contract).

> Azure was the first target and is discarded: the whole burstable B-series was
> blocked at subscription level. DigitalOcean turned out to be truer to the
> blueprint anyway — a droplet, root, a systemd unit, done.

## Where the shape comes from

This started with an innocent question — *"what's the difference between an EC2
and a VM?"* — whose answer was a machine already seen working for years at a
GPS-tracking company (EC-GPS): receivers push positions over GPRS to a **Perl
daemon** on an always-on Linux droplet, the daemon writes every packet to an
append-only `gps_logs` table, and a replaceable PHP console only **reads** it.
That skeleton has printed money for two decades.

AIRE is that machine, piece by piece:

| EC-GPS | AIRE today | AIRE next |
|---|---|---|
| GPS receivers push over GPRS | demo device pushes over TCP | apps push prompts over HTTP |
| Perl daemon on a port | `aire/listener.py` on :9099 | the engine that owns the SDK |
| writes `gps_logs`, append-only | appends to `aire.log` | mirrors the transcript to Postgres |
| PHP console reads and displays | `ssh` + `grep` | SSR paints the agent working, live |

Same skeleton; the parsing step becomes reasoning. The log and the socket are
eternal — AI is just the *transform* (the repo's law:
[`log-is-the-truth`](.claude/rules/log-is-the-truth.md)).

## Where it's going: a substitute AND an enhancer of the Claude API

AIRE is a substitute for the **Claude API** — not the SDK, not Claude.ai, the
API. Your apps stop calling `api.anthropic.com` and call AIRE: same slot (an
HTTP endpoint, not a library you import), but with two things the raw API will
never give you, selected by `?mode=`:

- **`complete`** — the substitute: a bare turn, no tools.
- **`agent`** — the enhancer: a full Claude Code session that executes tools.

And unlike the stateless API, **AIRE remembers and lets itself be watched**:

```
Accept: text/html          → a server-rendered page that writes itself as the agent thinks
Accept: text/event-stream  → the raw events, for your apps
```

No React, no npm, no build, no frontend. `GET /projects/avatar` → a page, with
the agent working, live. The first consumer is fi-runner (free-intelligence):
its apps call AIRE over HTTP instead of owning the SDK themselves.

### Why the memory MUST leave the process

In AIRE's very first live session, the agent answered on the streaming page,
reported its cost — and a page reload **erased the conversation**. Gone. That is
the exact failure this project exists to kill, and it's also what Claude Code
does to everyone at day 30: transcripts deleted silently, no recovery
([#59248](https://github.com/anthropics/claude-code/issues/59248),
[#62476](https://github.com/anthropics/claude-code/issues/62476),
[#61952](https://github.com/anthropics/claude-code/issues/61952)).

The SDK's `SessionStore` hook is the official cure — mirror the transcript to
your own database — and its docstring delegates retention to you in writing:

> *"Retention is the adapter's responsibility — implement TTL, object-storage
> lifecycle policies, or scheduled cleanup according to your compliance
> requirements."*

So two things are needed: the **mirror** and the **broom**. Verified by reading
their code, nobody has both:

| | Mirrors to a DB | Reusable HTTP server | Housekeeping |
|---|---|---|---|
| [`claude-cookbooks/hosting`](https://github.com/anthropics/claude-cookbooks/tree/main/claude_agent_sdk/hosting) (official) | ❌ in-RAM dict + disk | ⚠️ single project | ❌ |
| [Agno](https://github.com/agno-agi/agno) (41k ⭐) | ❌ in-RAM dict + disk | ✅ | ❌ |
| [ArcReel](https://github.com/ArcReel/ArcReel) (3.2k ⭐, AGPL) | ✅ | ❌ internal lib | ❌ |
| **AIRE** | ✅ | ✅ | ✅ |

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

- **The memory** — the transcript, in your Postgres. *The only irreplaceable
  piece: delete the container and AIRE lives on; delete the database and AIRE
  is dead.*
- **The work** — what the agent produces, in git. Separate on purpose.
- **The body** — the container. It's born, it works, it dies. It stores nothing
  because that's not its job. (The droplet is the body of the *chassis* phase;
  the memory will never depend on its disk.)

## What it is NOT

- **Not a VM runner.** The droplet hosts the daemon; the memory must never
  need it to survive.
- **Not a library.** You don't import it; you call it over HTTP from any
  language.
- **It doesn't reimplement the SDK.** The agentic loop, tools, subagents,
  permissions and sandbox belong to the SDK. AIRE is the missing glue.

## Status — honest

| Layer | State |
|---|---|
| Droplet + listener + device + CI/CD | ✅ **Live**, heartbeats accumulating 24/7 |
| Engine (SDK owner, `complete`/`agent` modes) | Written (`aire/engine.py`), local only |
| Streaming SSR + SSE (`aire/server.py`, `aire/render.py`) | Written, local only, no auth yet |
| Postgres mirror (`aire/store.py`, official adapter) | Copied and adapted, local only |
| **The tracer that proves the thesis** — chapter 1 → kill the process → chapter 2 remembers | ⏳ **Next** (backlog #5) |
| The broom (retention, backups, metrics) | Backlog |

The full roadmap lives in [`.claude/backlog/`](.claude/backlog/). The deep
context — the spirit, the genesis, the verified SDK facts, the discarded
routes — lives in [`CLAUDE.md`](CLAUDE.md).

## License

To be defined.
