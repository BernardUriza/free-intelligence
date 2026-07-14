# The device verb protocol — the daemon's write-command contract, and how it persists

Repo rule for `aire-server`, registered 2026-07-14 by Bernard's directive
("este feature nuevo debe persistir"). The listener's open port speaks a tiny
line protocol. Most lines are **reports** (append verbatim to the log, no auth —
EC-GPS fidelity: devices push). A few lines are **verbs** — commands that DO
something — and they are the daemon's write-command contract. This rule freezes
that contract and the persistence guarantees behind it, so the feature cannot
quietly rot or "disappear".

## The verbs (all token-gated by `AIRE_VERB_TOKEN`, all command-as-event)

| Verb | Line | Effect | Log event |
|---|---|---|---|
| MKDIR | `MKDIR <token> <name>` | create a session casita `workspaces/{ts}_{uuid}_{name}` | `MKDIR` + `FOLDER-CREATED` |
| ALLOW | `ALLOW <token> <ip> [note]` | add a device to the whitelist (`aire_device`) | `ALLOWED-DEVICE <ip>` |
| REVOKE | `REVOKE <token> <ip>` | remove a device from the whitelist | `REVOKED-DEVICE <ip>` |

Contract invariants (do not break without updating this rule):

1. **Token-gated, constant-time.** Every verb checks `AIRE_VERB_TOKEN` with
   `secrets.compare_digest`. A bad token → `DENIED` and a `*-DENIED` log line.
2. **Command-as-event.** The verb's action AND outcome are appended to the log
   like any other line; the **raw token never touches the log, the file, or
   Postgres** (redacted). The reply is a one-line ACK the client reads back.
3. **Reports need no token.** A plain line is appended (rate-limited per IP,
   `AIRE_RATE_LIMIT`). The port stays internet-open by design.

## The whitelist gate (backlog #18)

`AIRE_WHITELIST_ENFORCE=1` turns strict mode on: a non-loopback, non-whitelisted
peer gets a visible `DENIED-DEVICE` line and is hung up on (Carlos/EC-GPS failure
#1: a forgotten device goes mute → now you SEE it knocking). Default is OFF
(advisory: the roster works, nothing is blocked). **Populate the roster BEFORE
flipping enforce on**, or an empty table denies everyone.

Enforcement requires the daemon to READ the roster — the **second sanctioned
exception** to [[write-only-daemon]] (documented there). It is a startup load
kept in lockstep with the daemon's own ALLOW/REVOKE writes: no polling, no query
per connection.

## How the feature PERSISTS (the durability model — this is the point)

Three surfaces, three homes — none of them the droplet's mortal disk:

- **The code** (verbs, gate) → **git**. Reaches the droplet via CI
  (`git reset --hard origin/main`) and a fresh box via `infra/provision-do.sh`.
- **The roster data** (`aire_device`) → **the owner's Postgres**, created as role
  `aire` so the console reader sees it. Deathless: it survives the kill test
  exactly as the transcript does (Carlos failure #2: "the whitelist disappeared"
  — impossible here).
- **The operational config** (`AIRE_WHITELIST_ENFORCE`, the engine's tokens, the
  budget) → **`~/.secrets/` on Bernard's Mac**, composed into `/etc/aire/env` by
  `provision-do.sh`. The enforce knob lives in `~/.secrets/aire-whitelist.txt`
  so a re-provision restores the gate's STATE, not just its code.

The invariant: **a kill test (destroy → re-provision) must resurrect the FULL
feature — code, roster, and enforcement state — with nothing set by hand.** If a
new knob is added out-of-band, its `~/.secrets/` home and its `provision-do.sh`
line are part of shipping it, not an afterthought. A feature that only lives in a
running process or a hand-edited `/etc/aire/env` is NOT shipped (Art. 2, and the
litmus test: an un-reproducible box is a mortal body).

See also [[write-only-daemon]] (the read exceptions), [[log-is-the-truth]] (verbs
are events), and the playbook's `live-infra-changes-as-code` (hand-set config is
a landmine until it's restored by provisioning).
