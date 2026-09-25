# /soplo — is the air still blowing? (the pulse of AIRE's droplet)

Shows the live pulse of AIRE on its DigitalOcean droplet: whether the daemon and the
engine are still `active`, whether the memory answers, and the tail of the
append-only log. The air blows when the machine is up and the pen still writes.

> **The demo device is RETIRED** (2026-07-14, Bernard: *"ya no lo necesitamos"*). The
> The KEEPALIVE heartbeats are gone with their simulator (deleted 2026-08-22). The
> log now grows only from real events (VISIT beacons, MKDIR verbs, whatever knocks on
> the open port). **Absence of keep-alives is NOT a failure.** To bring the simulator

ARGUMENTS: optional `grep` filter for the log tail (default: no filter — show the last
lines as they are). E.g. `/soplo VISIT` shows the web beacons; `/soplo MKDIR` the
casitas.

## Instructions

### Single step — read the pulse (without hanging)

Run THIS command over SSH against the droplet (bounded: NEVER `tail -f` from the Bash
tool, it hangs forever — use `tail -n`):

```bash
ssh -i ~/.ssh/aire_vm -o ConnectTimeout=10 root@159.203.84.13 \
  'echo "== services =="; systemctl is-active aire-listener aire-server; \
   echo "== memory =="; curl -s --max-time 8 localhost:8088/health; echo; \
   echo "== pen =="; zgrep -ah "PEN-" /opt/aire/aire.log* | sort | tail -n 1; \
   echo "== last mirror write =="; grep -a "MIRROR" /opt/aire/aire.log | tail -n 1; \
   echo "== log tail =="; tail -n 8 /opt/aire/aire.log; \
   echo "== totals =="; printf "lines=%s casitas=%s uptime=%s\n" "$(wc -l < /opt/aire/aire.log)" "$(ls /opt/aire/workspaces | wc -l)" "$(uptime -p)"'
```

If ARGUMENTS were given, filter the tail: `tail -n 200 /opt/aire/aire.log | grep -- "FILTER" | tail -8`.

Also worth reporting when relevant: a long-running tmux session (`tmux ls`) — a book
being written, an agent still working with nobody attached.

### Report

In 2-3 lines, with real receipts (Art. 2 — never fake-green):

- **Still blowing?** Yes ONLY if `aire-listener` AND `aire-server` say `active`,
  `/health` returns `ok`, **and the last `PEN-` transition in the log is `PEN-UP`**
  (when the DSN is configured). Anything else is reported plainly (the air stopped
  blowing), with an offer to diagnose:
  `journalctl -u aire-listener -u aire-server --no-pager -n 20`.
- **The pen condition exists because of the NUL poison pill (2026-07-20):** the pen
  sat wedged for ~4.5 days flip-flopping PEN-UP/PEN-DOWN every 2s while both units
  were `active` and `/health` said `ok` — /soplo declared the air blowing over a
  frozen mirror. Units + `/health` measure the engine, NOT the pen; the pen's own
  distress signal is the `PEN-` line. A `PEN-DOWN` tail = the memory is not being
  mirrored = NOT blowing, whatever the other proxies say
  (docs/listener-doctrine.md, the pen section).
- **The pen line lives in the ROTATED logs too.** `PEN-` is a transition, not a
  heartbeat: it is written once when the pen changes state, and logrotate
  (`daily`, `rotate 7`) moves it out of `aire.log` within a day. That is why the
  command `zgrep`s `aire.log*` and sorts by timestamp. On 2026-09-25 a plain grep of
  the live file came back empty and /soplo reported the pen as unknown, while
  `aire.log.2.gz` held `PEN-UP` from 09-23.
- **No `PEN-` in the whole 7-day window** means no transition happened in that
  time, which is fine; it does not prove the pen is UP. Report it as "no pen
  transition in 7 days" and back it with the `last mirror write` line: a
  `CASITA-MIRROR stored` from today means the pen is writing to Postgres. If both
  are missing, you cannot tell whether the pen is working. Say that, and do not
  call it blowing.
- The last log lines and the totals (lines, casitas, uptime).
- If SSH fails / times out: **report it honestly** (droplet down or unreachable), never
  invent a pulse. Check the droplet state with
  `doctl compute droplet get aire-droplet --format Status,PublicIPv4`.

### For a continuous watch in YOUR terminal

Offer this one-liner (prefix it with `! ` to run it here, or paste it in any terminal):

```
! ssh -i ~/.ssh/aire_vm root@159.203.84.13 'tail -f /opt/aire/aire.log'
```

## Rules

1. **NEVER `tail -f` from the Bash tool** — it hangs the session. Bounded only
   (`tail -n`). The continuous follow is for the user's terminal, via `!`.
2. **Real state, no fake-green** (Art. 2): "blowing" requires both units `active` and
   `/health` ok, verified live. A dead service is reported dead.
3. **A quiet log is not a dead log.** With the demo device retired, silence is the
   normal state — do not report it as a failure.
4. **SSH down = report it** — never simulate a pulse. The droplet may be off.
   **But check the IP before you check the obituary.** On 2026-08-22 SSH timed out
   from this file's hardcoded address while the door answered `200` and DO reported
   the droplet `active`: the IP had changed and the skill was stale. A hardcoded
   address is a fake-RED generator. Resolve it live before declaring anything dead:
   `doctl compute droplet get aire-droplet --format Status,PublicIPv4`, and hit
   `https://gate.bernarduriza.com/health` — the public door outranks SSH in the rigor
   hierarchy, and it does not care what IP this file remembers.
5. **No emojis** unless the report calls for one (a closing 🌬️ is allowed — it is the
   soul of the project).

## Context

The droplet, the account and the whole deploy live in the project memory
`aire-do-deploy-context`. IP `159.203.84.13`, account `bernardurizadev`, systemd units
`aire-listener` (TCP :9099, the pen) + `aire-server` (HTTP :8088, the engine) +
`aire-sweep.timer` (the broom). Append-only log at
`/opt/aire/aire.log`; casitas at `/opt/aire/workspaces/`.
