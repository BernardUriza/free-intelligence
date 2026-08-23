# Every guard fails quietly — the disease behind a dozen findings

Status: **Three fixes shipped 2026-08-22; two decisions open (Bernard's)**
Proposed: 2026-08-22 by Claude (a structural review of the whole system, three
parallel sweeps: engine/gateway, listener/infra, front/contract)

## What it is

AIRE is meticulously defended against loud failures. `/health` catches every
exception. The mirror never fails the relay. A missing secret file "only
disables that one feature, loudly". Every one of those is good engineering.

Put together, they are a system where **no single missing knob ever produces a
red light**, and the audit found the same shape in module after module:

| The guard | How it goes off | What said so |
|---|---|---|
| the cumulative spend backstop (#25) | `AIRE_MAX_SPEND_USD` absent → `exhausted()` always `False` | nothing |
| the credential rotor (#31) | one slot configured → nothing to fail over TO | nothing |
| the device verbs | `AIRE_VERB_TOKEN` absent → every MKDIR answers `DENIED`, indistinguishable from an attack | nothing |
| the pen and the roster | `AIRE_DATABASE_URL` absent → `listener.py` skips them with no `else` branch and logs `LISTENING` | nothing |
| lending (#32e) | `AIRE_LEND_*` absent → invited keys get a 503 they cannot act on | nothing |
| the whitelist gate (#18) | `=0` → advisory only | the rule, not the box |
| **the reader wall** | the role or its default-ACL vanishes → the front goes blind | nothing |

And `/health` answered `{"status": "ok"}` for **all of them at once**, because
reachable memory was the only thing it ever proved. That is
[[verify-before-assuming]] Rule 22 exactly: a signal that cannot go red proves
nothing, and this one had been the daemon's only vital sign since day one.

## The worst instance: the reader wall was never provisioned

`provision-do.sh` composes twenty-odd knobs from `~/.secrets/` so that
destroying the droplet and re-provisioning resurrects the full daemon — the kill
test [[device-verb-protocol]] demands. But **the droplet is the mortal half.**
The memory lives in the owner's Postgres, and the two roles plus one default-ACL
that make the whole two-halves architecture real ([[write-only-daemon]]: the
daemon holds the pen, the front holds only `aire_reader`) were **never
provisioned at all**. Verified 2026-08-22: `ALTER DEFAULT PRIVILEGES` and
`CREATE ROLE aire_reader` appear nowhere in the repo as executable code. The
only record was a comment inside `~/.secrets/aire-postgres-readonly.txt`:
*"created: 2026-07-13 by devadmin."*

So a restored backup, a rebuilt Postgres server, or one dropped role would take
the front's eyes out, and nothing here could put them back. The likeliest repair
under pressure is handing the front the pen — the single failure the rule exists
to prevent, and the one that already happened once (`'pwned'` at `aire_log`
seq 2641).

## What shipped (2026-08-22)

1. **`aire/arming.py` + `/health`.** One place enumerates every guard and says
   whether it is armed; `/health` carries `armed` and a `disarmed` list. It
   reports state, never values — a count of credential slots, never a token.
   costwatch now goes red on any **undeclared** disarmed guard, so a safety
   cannot go off with nobody deciding it. Two are declared: `whitelist_enforce`
   (deliberate — an empty roster would deny every device) and
   `credential_failover` (**not** deliberate; see below).
2. **`infra/wall.py` + `infra/lib/pgwall.sh`.** The reader wall as code. It
   grants what the daemon's own role may (it owns the tables) and ASSERTS the
   rest, failing the provision with the exact admin SQL when the role is gone —
   `aire` has neither SUPERUSER nor CREATEROLE, so that half is honestly
   escalated instead of pretended. Proven able to go red twice on a throwaway
   database (role missing; role present but no grants), to repair, and to make a
   table created AFTER the wall readable. Also wired into costwatch nightly, and
   into `ci-front.yml`, which until now built the wall with a *different owner
   role* and a snapshot `GRANT` — testing a look-alike instead of the mechanism.
3. **The concurrency slot's lifetime** (`lending.claim/hand_off/release`, and
   the door extracted to `aire/door.py`). The gateway door claimed a slot in the
   middleware and returned it in the relay — two different layers — so a request
   that reached **no handler at all** kept it forever. Measured: two POSTs to an
   undefined `/v1/` path left `_inflight` at MAX and the next real
   `/v1/messages` answered 429, until the daemon restarted. An invited key could
   lock itself out with two typos. Fixed, with two regression tests.

Also tightened while in there: `engine/memory_tool.py` connected to Postgres
with **no timeout** (every sibling call site passes one) and ran an unindexable
`ILIKE` over the whole transcript inside a paid turn — it now carries a connect
timeout and a statement timeout, because a scan that grows forever does not
fail, it stalls with the bill running.

## The decisions that are the owner's

1. ~~**The rotor holds ONE slot.**~~ **STALE — corrected against the box
   2026-08-22.** `/health` reports `credential_slots: 2` and
   `credential_failover: true`, and `/etc/aire/env` carries
   `ANTHROPIC_API_KEY_FALLBACK` with a real 108-char `sk-ant-` value beside
   `CLAUDE_CODE_OAUTH_TOKEN`. So a metered key WAS minted, the rotor walks two
   slots of DIFFERENT kinds — not the same-account placebo `CLAUDE.md` warns
   about — and #31's failover machine has fuel. This paragraph claimed the
   opposite for as long as it took someone to read `/health` with a token.

   ~~**What that unlocks…**~~ **DECIDED AND SHIPPED 2026-08-22, Bernard's call.**
   The box lends `AIRE_LEND_API_KEY` now, derived in `secrets.sh` from the file
   the metered key already sits in — not copied into a file of its own, because
   a secret in two files is a secret that gets rotated in one. `AIRE_LEND_OAUTH_TOKEN`
   stays as a fallback in code that provisioning no longer writes.

   Verified on the box, and the first two probes were MINE being wrong, not the
   code: an out-of-band `mint()` never reaches the daemon's cache, and an AIRE
   key presented as `x-api-key` is not presented at all (the door reads the
   Bearer, or `x-aire-key`). With the right header, a real invited turn relayed
   and answered, `aire_token` banked **$0.00005 against its own $0.25 ceiling**,
   the mirror row carries `holder = lendswitch-probe`, and a `mode=complete`
   turn on the engine's own credential answered in the same minute — the two
   halves are independent now. Probe key revoked.

   **The residual coupling is named, not hidden:** that metered key is also the
   rotor's slot 3 (#31), so a stranger spends on what the engine falls back to.
   Splitting them is one more key and one more file, the day it matters.

2. **Whether the daemon should refuse to start with a guard it expects armed.**
   Reporting is strictly better than silence, but it is still a report. A
   `AIRE_REQUIRE_ARMED` list that fails the process closed is the stronger
   version, and it is a bigger hammer than this review should swing alone.

## Left on the table, deliberately (found, not fixed)

Each is real, none is bleeding; filed here rather than half-fixed:

- ~~**Two env vars name one database.**~~ **FIXED 2026-08-22** — the hard
  cutover, Bernard's call over an alias. `AIRE_DSN` is gone from the daemon and
  from `secrets.sh`; `AIRE_DATABASE_URL` is the only name, and an absent one now
  RAISES (`deps.MissingDSN`) instead of defaulting to a laptop. The two
  hardcoded `postgresql://bernardurizaorozco@127.0.0.1` fallbacks are deleted,
  and `arming.py`'s `pen` and `store` guards collapsed into one `database` — they
  had been watching the same value under two names, so `/health` implied two
  independent memories. Pinned by `tests/test_dsn.py`, whose two structural
  checks were proven to go red by seeding a regression before they were trusted.
- ~~**Five ways to reach Postgres.**~~ **FIXED 2026-08-22.** Re-measured against
  the real database before touching anything: **185–236 ms to connect, 12–29 ms
  to run the query**, and a warm `acquire()` on the same box costs **0.0–0.6 ms**.
  All five connect-per-call sites (`tokens`, `access`, `sweep`, `roster`,
  `memory_tool`) now share one lazy per-process pool in `aire/db.py`. Bernard
  chose uniformity over lifetime-fit — the broom is a oneshot that gains nothing
  from a pool, and it uses the same door anyway, closing it on the way out.

  What stayed on direct connections, because their lifetime was already right:
  the store's pool, the gateway mirror's pool, the pen's long-lived reconnecting
  connection, and `mirror`/`restore`, which each open one connection for one
  oneshot run. A structural test names that whitelist, so the next call site
  that opens its own goes red instead of quietly paying the toll again.

  The hazard a pool introduces and a fresh connection never had: `memory_tool`
  set `statement_timeout` as a connection-level server_setting, which on a
  pooled connection would outlive the query and cap the next borrower's. It
  rides as `SET LOCAL` inside a transaction now, pinned by its own test.
- ~~**The kill test verifies fewer units than a routine push.**~~ **FIXED
  2026-08-22.** `remote-bootstrap` now checks the same six `deploy-server.yml`
  does. A kill test weaker than a deploy is not a kill test — the two it skipped
  were `aire-tmpclean.timer` and `aire-mirror.timer`, the second being exactly
  the unit whose job is to prove the SSH door's memory leaves the mortal disk.
- ~~**ALLOW/REVOKE have no exception handling around their Postgres write.**~~
  **FIXED 2026-08-22.** They logged only success, so a Postgres blip erased the
  whole attempt: no command line, no failure line, and no ACK — the exception
  walked out through the connection handler, which appended `DISCONNECT` and hung
  up. Now every accepted verb writes two lines like MKDIR always did (the command,
  then its outcome), every failing path ends in `ALLOW-ERROR`/`REVOKE-ERROR` and
  an `ERROR` reply, and the contract table in [[device-verb-protocol]] says so.
- ~~**`pen.write()` discards on `QueueFull` with no `PEN-OVERFLOW` line.**~~
  **FIXED 2026-08-22.** Dropping is correct — the file holds every line and the
  mirror is the copy — but an unmarked drop is two memories diverging in silence,
  and the front reads the mirror, where a hole with no marker looks like a quiet
  stretch. The gap is now bracketed at both ends: one file line when it opens, and
  a counted `PEN-OVERFLOW n lines never reached postgres` that goes into the
  MIRROR when it closes. Both regressions are pinned in `test_listener.py`, and
  both tests were run against the old code first to watch them go red.
- ~~**The listener has no read/idle timeout.**~~ **FIXED 2026-08-22** (`d065634`),
  and this line survived the fix by a day. Two windows, not one knob: 300s of idle
  for a device that has already spoken, 10s to finish the FIRST line — with a
  single window a reconnecting attacker keeps the door jammed forever.
- ~~**costwatch never checks logrotate**, though [[do-budget]] and the listener
  unit both state that it does.~~ **FIXED 2026-08-22 — the code caught up to the
  documentation instead of the documentation being downgraded.** Four signals,
  because a config that validates is not a rotation that happens: the config
  parses, `logrotate.timer` is active, the last rotation in
  `/var/lib/logrotate/status` is at most three days old, and `aire.log` is under
  64 MB. All three red paths (never rotated / stale / oversized) were provoked on
  the droplet before the check was trusted, and its state file was put back.
- ~~**The front's `tables()` has no per-table fault isolation**, and
  `claudeFolders()`/`gatewaySessions()` aggregate whole tables with no window.~~
  **FIXED 2026-08-22 — and the measurement moved the aim before a line was
  written.** Against the real database: `aire_gateway_log` is 1,173 rows (51 MB
  of fat bodies, not many rows) and its full aggregate runs in **1.3 ms**, so an
  index there would have been ceremony. The one slow query was
  `claudeFolders` at 110 ms, and decomposing it named the cost exactly:
  `max(mtime)` 2.5 ms, `count(DISTINCT session_id)` 1.0 ms,
  **`sum(length(entry::text))` 56.6 ms** — serializing every jsonb row to text
  on every render, for a number that never changes after the row is written. A
  covering index was tried and dropped: the planner would not take it, and
  forcing it off seq scans changed nothing, because the cost was never the scan.

  What fixed it is the pattern `store.py` already carried one of — a STORED
  generated column beside `entry_uuid`. **110 ms → 2.9 ms on production**, same
  number, 1537 of 1537 rows agreeing to the byte, with the ALTER doing the
  backfill (a `CREATE TABLE IF NOT EXISTS` is a no-op on a live table, so the
  column would never have reached production from the DDL alone).

  `tables()` counts each table in its own try now: one unreadable table costs
  its own row, not the page. `front/scripts/blind-table.ts` proves it against a
  real database with real grants, in the attack job that already builds both
  roles, and it was watched fail with the old code.

  And the finding underneath the finding: the gateway's lists showed the newest
  60 and stopped, while the log holds **237 conversations** — 177 of them
  unreachable from the console of a repo whose law is that the log is the truth.
  Both lists take a keyset cursor now (the page's own `seq`, never an OFFSET
  that re-walks what it skips and shifts under a live log).
- ~~**`aire-server` has no `MemoryMax` and `aire-listener` no `OOMScoreAdjust`**~~
  **FIXED 2026-08-22.** The pen now carries `MemoryLow=32M` + `OOMScoreAdjust=-900`
  (applying it pulled 11 MB of the pen out of swap); the engine carries
  `MemoryHigh=200M` / `MemoryMax=280M` / `OOMScoreAdjust=200`, because it is the
  half that may safely die. The numbers cost three measured rounds and killed two
  of my guesses: 68 MB was an IDLE reading (a real agent turn is ~200 MB), the
  heap is ELASTIC so raising the ceiling only raises the peak, and tightening the
  engine did NOT keep the pen resident — the pen's swap got WORSE. All three
  rounds are written into the unit so nobody re-derives them.

## Status / next step

Shipped and verified. `/health` now reports its own guards; the wall is code
with a red it can reach; the slot leak is closed with tests.

**All eight leftovers are closed (2026-08-22, second pass)** — the two
silent-divergence ones in the listener, the kill test's missing units, the
logrotate watch, the idle timeout that had already shipped, the five ways to
reach Postgres, and the front's three. What is left in this item is the two
forks that were always Bernard's, below.

See also [[verify-before-assuming]] Rule 22 (the signal that cannot fail),
[[device-verb-protocol]] (the kill test this extends past the droplet),
[[write-only-daemon]] (the wall itself),
[#41](41-the-mirror-stores-the-conversation-n-times.md) (the other thing growing
in silence), and [[00-constitution]] Art. 2.
