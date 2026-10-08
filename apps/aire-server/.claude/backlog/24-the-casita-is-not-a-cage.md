# The casita is not a cage — an agent can read the daemon's secrets

Status: **Fixed 2026-07-20** (`e2ff4f7`) — verified live. The daemon still runs
as root (that half stays Bernard's infra call), but a `PreToolUse` hook now cages
every file tool to the casita, so root-ness no longer means an agent can roam.
Proposed: 2026-07-20 by Claude (measured, not theorised)

## What shipped, and the correction it forced

The canonical fix named below (`SandboxSettings`) turned out to be WRONG when
checked against the SDK source: SandboxSettings confines only bash. Its docstring
sends filesystem reads to a permission gate. The first attempt used the
`can_use_tool` callback — and a live test disproved it: under `acceptEdits` a
`Read` is auto-allowed, the callback never fires, and the agent read
`/etc/aire/env` straight through it. The gate that actually holds is a
**`PreToolUse` hook** (`engine/cage.py`), which runs before every matched tool
regardless of permission mode. Verified live: `Read /etc/aire/env` → *"denied:
… outside the casita"*, `Write /tmp/fuera.md` → denied, `Write hola.md` in the
casita → created. Disk confirmed: no secret leaked, `/tmp` untouched.

The CLAUDE.md claim that "SandboxSettings confines the agent" was corrected the
same commit — it was the fourth false claim this repo's own rule warns about,
caught by verifying against the source.

## What it is

`options.py` already warns in writing that *"the real filesystem confinement is
`SandboxSettings`, not yet in place — `cwd` is NOT a cage."* What nobody had
measured is the consequence: **`mode=agent` keeps `Read`/`Grep` allowed and
`cwd` confines nothing, so an agent launched by ANY consumer can read every file
on the droplet — including `/etc/aire/env`**, which holds `AIRE_AUTH_TOKEN`, the
Postgres DSN *with its password*, `AIRE_VERB_TOKEN` and `CLAUDE_CODE_OAUTH_TOKEN`.

Measured through the AIRE door, from outside the box:

```
TOOL: Read {'file_path': '/opt/aire/README.md', 'limit': 1}     → "# AIRE"
TOOL: Grep {'pattern': '^', 'path': '/etc/aire/env', 'count'}   → 7 lines
```

**It already bites in NORMAL use, not just under a probe.** In an E2E on
2026-07-20 — two books written in parallel through the door, no adversarial
intent — one agent (`el-ajedrez`) chose absolute paths and wrote its whole book
to **`/tmp/ajedrez/`**, entirely outside its casita, while the other (faros)
used relative paths and stayed in. The transcript still mirrored to Postgres for
both (the memory is safe), but the ARTIFACTS landed in `/tmp` — outside
`workspaces/`, so the "fetch by hand from the casita" model misses them and a
`/tmp` sweep would erase them. The cage's absence is not a hypothetical hole a
hostile prompt must find; a well-behaved agent falls out of the casita on its
own.

The probe deliberately asked for the line COUNT, not the contents — a hostile or
merely curious prompt would ask for the contents and get them. `Bash` being
disallowed does not help: `Read` alone is enough.

**The second blast radius is the memory.** The transcript mirrors to Postgres, so
a secret read into a turn is written into the append-only store forever — and the
store is what the front renders at `/claude`. A leak would be permanent by design
([[log-is-the-truth]]: correcting means appending, never erasing) and visible in
the console.

## Canonical path to reuse (Art. 6)

`SandboxSettings` — the SDK's own confinement, already named in `CLAUDE.md`'s
verified facts as the mechanism for "the container that doesn't self-modify" and
described there as **config, not infra**. Do not invent a path allowlist in
application code: wire the SDK's sandbox into `build_options`, scoped to the
session's casita.

Second layer, cheap and independent: the secrets do not have to be READABLE by
the agent's uid at all. `/etc/aire/env` is delivered by systemd's
`EnvironmentFile` to the process; a `chmod 600` + a non-root service user would
put the file out of reach even if the sandbox is bypassed. That change also
retires the `bypassPermissions`-is-refused-as-root problem (see #23's sibling
finding) — running as root is what forced `acceptEdits` in the first place.

## The decision that's the owner's

**How much of the droplet an agent is allowed to see.** Reading `/opt/aire`
(the repo, already public on GitHub) may be perfectly fine and even useful; the
secrets are not. Bernard decides whether the cage is the casita, the repo, or
something in between — and whether the daemon stops running as root, which is a
provisioning change with real blast radius on a box that is also his Linux
curriculum.

## Status / next step

Not built. Nothing about this is urgent while the only consumer is Bernard
himself and `AIRE_AUTH_TOKEN` gates the door — but the moment a third party can
POST a prompt, this is the hole they walk through.
