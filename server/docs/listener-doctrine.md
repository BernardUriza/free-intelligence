# The listener's doctrine — the long-form rationale behind `aire/listen/`

The narratives that used to live as comments inside the monolithic
`listener.py` (521 lines, gutted 2026-07-19 under the thirty-line law). The
code now states each rule in one line and points here; this file keeps the
full reasoning so it is never lost. Module map at the bottom.

## The chassis (no intelligence)

The eternal chassis, bare: `accept()` → read lines → **append to the log**. It
is the EC-GPS daemon — an always-on service listening on a TCP port — without
the Perl and without the brain. The AI (engine/render/store) sits AFTER,
between the `accept()` and the append. Today it isn't here: on purpose.

Every line arriving from a device is appended, as-is, to an append-only log
(`aire.log`), with a timestamp and the peer. Greppable, which is the whole
point: `tail -f aire.log | grep KEEPALIVE`. On the droplet, "SSH in and grep"
is literally the EC-GPS experience, recreated.

## The verbs (`AIRE_VERB_TOKEN`)

`MKDIR <token> <name>` asks the daemon to create a session casita — a fresh
workspace folder `workspaces/{timestamp}_{uuid4}_{name}` where a future
agent-mode session will live. Every session is born new — the uniqueness is
the point. Verbs are gated by a long token that lives only on Bernard's Mac
and in `/etc/aire/env`; the port stays internet-open, but ordering requires
the family password. Reporting (plain lines) needs no token. Command-as-event:
the token-redacted command and its outcome are appended like any other line,
and the client gets a one-line ACK. Contract frozen in
`.claude/rules/device-verb-protocol.md`.

## The pen (`AIRE_DATABASE_URL`)

EC-GPS welds its `gps_logs` to the droplet's disk: if the box dies, the memory
dies with it. AIRE's one evolution is ripping the memory out of the mortal
body: when the DSN is set, every appended line is ALSO written to an
append-only table (`aire_log`) in the owner's Postgres. The local file stays
as the greppable view; the table is the memory with no body to lose. No DSN →
pure EC-GPS mode, file only. The same line, mirrored verbatim, never parsed.

- **Order is sacred**: a batch that failed to insert is HELD and retried first
  on reconnect — never re-queued to the tail. The front reads `ORDER BY seq`;
  order must match the events.
- **The NUL poison pill (the 6-day outage, 2026-07)**: NUL is valid UTF-8, so
  `errors="replace"` lets it through — but Postgres `text` can never hold it.
  One binary probe on the open port wedged the pen in an infinite retry loop
  for ~6 days, flip-flopping PEN-UP/PEN-DOWN every 2s. Cure, in two layers:
  neutralize NUL at the mouth (`listen/net.py`), and on `DataError` (SQLSTATE
  22xxx — Postgres answered and REJECTED; an identical retry can NEVER
  succeed) fall back to line-by-line mirroring with pop-as-committed
  (`listen/pen.py`). A line unstorable even sanitized becomes a `PEN-POISON`
  marker; the file keeps the raw original.

## The floods (rate limit + connection caps)

The port is open to the internet by design (EC-GPS: devices push, no auth to
report). That makes the pen a WRITE AMPLIFIER: every accepted line lands in
the owner's Postgres. Without a ceiling, a stranger with a for-loop fills the
disk AND inflates the bill. So: a token bucket per peer IP — generous for a
real device (a keep-alive every 2s is 30/min), fatal for a flood. Loopback is
exempt (it is us). Enforced per LINE, not per connection: reconnecting does
not reset the bucket. Rejections hang up WITHOUT appending — a rate-limit
notice per flooded line would BE the flood (one `RATE-LIMITED` line, then
silence).

The bucket stops a LINE flood; the connection caps (total + per-IP) stop a
CONNECTION flood — many sockets each sending little — from exhausting fds/RAM
on the 512MB box (ufw allows the port from anywhere; fail2ban only watches
sshd).

## The whitelist gate (backlog #18)

Truth in Postgres (`aire_device`), NOT a file on the mortal droplet disk (the
exact "the whitelist disappeared" EC-GPS failure). Enforcement requires the
daemon to READ it: the second sanctioned exception to `write-only-daemon`.
FAIL CLOSED: when enforcing, a non-loopback peer is denied unless the roster
is loaded AND lists it — a DB blip at boot must not silently open the gate; a
security control that self-disables on a hiccup is worse than none. The
`DENIED-DEVICE` line cures Carlos's failure #1: a forgotten device no longer
goes mute — you SEE it knocking. Enforcement is OFF by default (advisory);
populate the roster BEFORE flipping `AIRE_WHITELIST_ENFORCE=1`. The table is
created as role `aire` so the console's reader sees it.

## Module map

Flat, one concept per module (thirty-line law as amended 2026-07-20: the
original 30-line-per-FILE cut produced ravioli subpackages, flattened the
next day — functions ≤30, files ≤150, depth ≤2):

| Module | The concept |
|---|---|
| `listen/config.py` | every env knob |
| `listen/applog.py` | `_now`, `append` + the mirror registry |
| `listen/tasks.py` | `spawn` — strong task refs (create_task keeps only weak ones) |
| `listen/pen.py` | the Postgres mirror: queue, batches, drain loop, poison cure |
| `listen/roster.py` | the whitelist: cache, load/refresh, writes, boot |
| `listen/guards.py` | `Bucket` (line flood), `ConnLimiter` (socket flood), `admit` |
| `listen/verbs.py` | token auth, MKDIR/ALLOW/REVOKE, dispatch |
| `listen/net.py` | peer/hangup, line sanitizing, session, handle |
| `aire/listener.py` | the orchestrator entrypoint (`python3 -m aire.listener`) |
