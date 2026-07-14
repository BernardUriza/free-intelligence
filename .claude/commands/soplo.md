# /soplo — is the air still blowing? (the heartbeat of AIRE's droplet)

Shows the live pulse of AIRE's daemon on its DigitalOcean droplet: whether the
services are still `active` and the latest keep-alives the `app-demo-device` is
pushing. A keep-alive is a heartbeat — this asks whether the air is still blowing.

ARGUMENTS: optional `grep` filter (default `KEEPALIVE`). E.g. `/soplo MESSAGE`
shows the random messages; `/soplo .` shows everything.

## Instructions

### Single step — read the pulse (without hanging)

Run THIS command over SSH against the droplet (bounded: NEVER `tail -f` from the
Bash tool, it hangs forever — use `tail -n`):

```bash
ssh -i ~/.ssh/aire_vm -o ConnectTimeout=10 root@143.198.9.173 \
  'echo "== services =="; systemctl is-active aire-listener aire-device; \
   echo "== latest =="; tail -n 30 /opt/aire/aire.log | grep -- "FILTER" | tail -8; \
   echo "== total =="; printf "keepalives=%s lines=%s\n" "$(grep -c KEEPALIVE /opt/aire/aire.log)" "$(wc -l < /opt/aire/aire.log)"'
```

Substitute `FILTER` with the ARGUMENTS (or `KEEPALIVE` if no argument was given).

### Report

In 2-3 lines, with real receipts (Art. 2 — never fake-green):

- **Still blowing?** Yes ONLY if BOTH services say `active`. If either says
  anything else, say it plainly (the air stopped blowing) and offer to diagnose
  with `journalctl -u aire-listener -u aire-device --no-pager -n 20`.
- The accumulated **keep-alive count** (how many heartbeats so far) and the last
  3-4 log lines.
- If SSH fails / times out: **report it honestly** (droplet down or unreachable),
  never invent a pulse. Check the droplet state with
  `doctl compute droplet get aire-droplet --format Status,PublicIPv4`.

### For a continuous watch in YOUR terminal

Offer this one-liner (prefix it with `! ` to run it here, or paste it in any
terminal):

```
! ssh -i ~/.ssh/aire_vm root@143.198.9.173 'tail -f /opt/aire/aire.log | grep KEEPALIVE'
```

## Rules

1. **NEVER `tail -f` from the Bash tool** — it hangs the session. Bounded only
   (`tail -n`). The continuous follow is for the user's terminal, via `!`.
2. **Real state, no fake-green** (Art. 2): "blowing" requires BOTH services
   `active`, verified live. A dead service is reported dead.
3. **SSH down = report it** — never simulate a pulse. The droplet may be off.
4. **No emojis** unless the report calls for one (a closing 🌬️ is allowed — it is
   the soul of the project).

## Context

The droplet, the account and the whole deploy live in the project memory
`aire-do-deploy-context`. IP `143.198.9.173`, account `bernardurizadev`, systemd
services `aire-listener` + `aire-device`, append-only log at `/opt/aire/aire.log`.
