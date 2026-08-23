# Nothing had ever proved the door can COMPLETE a turn

Status: **Done 2026-08-23** — the canary rides the deploy and the nightly watch
Proposed: 2026-08-23 by Claude (auditing the backbone at Bernard's ask, "cómo
mejorar más este backbone")

## What it was

Every automated check this repo owned measured **liveness**, and not one of them
could go red while the engine was dead:

| The check | What it proves | Green with a dead engine? |
|---|---|---|
| `systemctl is-active` (deploy, per unit) | a process exists | **yes** |
| `logrotate --debug` | a config parses | yes |
| `/health` (costwatch, over localhost) | Postgres answers a `list_sessions` | **yes** |
| `arming.report()` | env vars are set | yes |
| growth / broom / disk / wall | the database is not running away | yes |

This is the repo's own doctrine turned on itself — [[verify-before-assuming]]
Rule 22: *"if the thing I am verifying were completely broken right now, would
this command still return green?"* For the daemon's whole reason to exist —
completing a turn — the answer was yes for every check on the box.

It is not hypothetical. `CLAUDE.md` already records the shape:
`permission_mode="bypassPermissions"` is refused when the process runs as root,
so **every `mode=agent` turn died with `ProcessError` exit 1 while `/health`
stayed ok** — "a defect invisible to `/health`", in the file's own words. The
same silence covers a dry credential rotor (#31), a `claude` binary lost from
the image, a Caddy relaying to nothing, an expired certificate, and the burned
weekly pool that returns a LYING SUCCESS.

## What shipped

`server/scripts/canary.sh` — one real turn through the **public** door, run
from **outside** the droplet (the GitHub runner), asserting the only chain that
cannot be faked: DNS → TLS → Caddy → Bearer → the SDK → Anthropic → an SSE
`result` carrying text and a nonzero cost under a ceiling.

- **The deploy's last word** (`deploy-server.yml`): a green deploy now means the
  code on the box served a turn, not that six units are active. Red prints the
  previous SHA and the rollback command — printed, never automatic, because the
  canary also goes red when Anthropic is down and undoing a good deploy over a
  vendor blip is a wrong action taken confidently.
- **The nightly watch's last word** (`costwatch.yml`), for the failures that
  arrive without a deploy: a revoked credential, an expired cert, a rotor gone
  dry.
- **Its own consumer slot**, `AIRE_PULSE_TOKEN` (`bearer.py`), a GitHub secret,
  a `~/.secrets/aire-pulse-token.txt`, and a line in `infra/lib/secrets.sh` so a
  re-provision restores it ([[device-verb-protocol]]'s persistence model).
  Revocable alone: emptying one variable kills the canary and disturbs no
  sibling consumer.

**What it costs, measured before it was written** (2026-08-23, a real turn
through `gate.bernarduriza.com`): **$0.028** in 11.5s — haiku, `mode=complete`,
`13,598` cache-creation tokens for the system prompt, which is what a cold
session pays even in the cheap mode. Daily + per deploy ≈ **$1/month**. The
ceiling `AIRE_CANARY_MAX_USD=0.15` makes the canary red if that stops being
true, which is its own small piece of budget news.

## What it does NOT cover

- **Mean time to detection is still a day.** The canary fires on deploys and at
  13:17 UTC. A door that dies at 14:00 is discovered ~23h later. A cheap
  external `/health` pulse every few minutes would cut that — and it must be
  external, because a watchdog on the box cannot report the box being gone.
  Not built; a scheduled GitHub cron burns Actions minutes and a third-party
  uptime monitor is an account to own. **Bernard's call.**
- **`mode=agent` is untested.** The canary runs `mode=complete`, which is the
  cheap notch — and the founding defect (root + `bypassPermissions`) killed
  precisely the notch this canary does not exercise. A second agent-mode canary
  costs more per run; whether the coverage is worth it is open.

See also [#25](25-no-cumulative-ceiling.md) (the other half of this audit: the
cumulative backstop resets on every restart, so a ceiling that reads "armed" is
counting from zero several times a day), [[do-budget]] (never watch only the
cloud where the spend is frozen) and [[ssh-is-a-missing-endpoint]] (a capability
is shipped when a curl from OUTSIDE the droplet exercised it).
