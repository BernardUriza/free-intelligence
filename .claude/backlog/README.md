# Backlog — AIRE

One line per item; the reasoning lives in the item's own file. It did not, until
2026-08-22: this index had grown to **28 KB with rows averaging 686 characters** —
an archive wearing an index's clothes, and the one file here anyone actually
scans. The prose moved into the files that already existed, and the sixteen old
rows that had no file at all became [`00-the-chassis-phase.md`](00-the-chassis-phase.md),
verbatim. Nothing was deleted (Art. 5); it was put where it belongs.

Shape and law: [[backlog-handling]] — one markdown file per item, this index
kept honest, a status flipped the day it changes.

## Live

| # | Item | Status |
|---|------|--------|
| [25](25-no-cumulative-ceiling.md) | No cumulative spend ceiling is set | Ledger shipped 2026-08-23; refusal stays per-process by decision |
| [28](28-per-token-budget.md) | Per-token budget | Done for INVITED keys 2026-08-11 (#32d); the 2 CONSTANT keys stay uncapped |
| [31](31-credential-failover.md) | Credential failover | **Rotated live 2026-09-03** on a 5-h session limit the detector had missed (fixed `1fecad8`); open: cooldown ignores the reset time, $1 cap does not bound a turn |
| [37](37-the-mode-dial-is-coarse.md) | The mode dial is coarse | Proposed 2026-08-22 |
| [39](39-two-slots-for-a-fleet.md) | Two slots for a fleet | Proposed 2026-08-22, MEASURED the same day |
| [40](40-every-guard-fails-quietly.md) | Every guard fails quietly | All 8 leftovers shipped 2026-08-22; 2 decisions open (Bernard's) |
| [42](42-the-guards-are-observational.md) | The guards ride observational | Observational half Done 2026-08-22; the buffered half Proposed |
| [43](43-nothing-ever-proved-the-door-serves.md) | Nothing ever proved the door can complete a turn | **Done 2026-08-24** — both notches, plus a 5-min external pulse |

## Closed

| # | Item | Status |
|---|------|--------|
| [7](07-backups.md) | Scheduled backups. | Done |
| [8](08-metrics.md) | Metrics per casita: weight, sessions, cost. | Done 2026-09-01 — cost shipped (52fe5e3); #25's ledger was the missing persistence |
| [19](19-thirty-line-compliance.md) | The thirty-line compliance refactor | Done 2026-07-20 |
| [20](20-monorepo.md) | The monorepo | Done 2026-07-20 |
| [21](21-bridge.md) | The bridge | Dropped 2026-07-20 |
| [22](22-the-endpoints-ssh-was-covering.md) | The endpoints SSH was covering | Done |
| [23](23-the-budget-cap-lies-twice.md) | The budget cap lies twice | Fixed 2026-07-20 (751e445) |
| [24](24-the-casita-is-not-a-cage.md) | The casita is not a cage | Fixed 2026-07-20 (e2ff4f7) |
| [26](26-the-mirror-relogs-everything-every-minute.md) | The mirror re-reads everything every minute | Fixed 2026-08-20 (c9d707b) |
| [27](27-nobody-sweeps-the-droplet-tmp.md) | Nobody sweeps the droplet's /tmp | Done 2026-07-20 (f55cef4) |
| [29](29-grow-the-door-per-turn.md) | Grow the door | Done 2026-08-20, both sides |
| [30](30-the-gateway-door.md) | The gateway door | Done |
| [32](32-the-nickname-door.md) | The nickname door | Done 2026-08-11 |
| [33](33-consumers-should-name-themselves.md) | Consumers should name themselves | Done 2026-08-12 |
| [34](34-meter-the-pass-through.md) | Meter the pass-through | Done 2026-08-21 (f0195a6) |
| [35](35-the-consumer-map.md) | The consumer map | Done 2026-08-29 — fleet single-backend (fi 70ac4062); learned + IaC closed 2026-09-01 (fi PR #455) |
| [36](36-the-living-casita-prompt.md) | The living casita prompt | Done 2026-08-21; its persona made deathless 2026-08-22 |
| [38](38-the-model-is-ignored-on-a-warm-session.md) | The model a turn asks for is silently ignored on a warm session | Fixed 2026-08-22 (21f5ee7) |
| [41](41-the-mirror-stores-the-conversation-n-times.md) | The mirror stores what the log already holds | Done 2026-08-22 (225cb72+8b301ae) |
| [44](44-the-caller-cannot-ask-if-a-session-exists.md) | A caller had no way to ask whether a session exists — so it replayed | Done 2026-08-24 |
| [45](45-the-glass-box-was-dark-on-this-door.md) | The glass box was dark on this door — `task_tracker` joins the registry | Done 2026-08-24 |
| [46](46-the-corpus-lives-in-the-owners-database.md) | `rag_store` joins the registry — the corpus lives in the owner's database | Done 2026-08-24 |
| [47](47-only-the-model-can-write-a-corpus.md) | Only the model could write a corpus — the door the upload was missing | Done 2026-08-24 |
| [48](48-remote-tools.md) | Remote tools — the caller's own HTTP MCP | Done 2026-08-28 (E2E receipt: Insult via mcp_http); file corrected 2026-09-01 |
| [49](49-a-second-provider-behind-the-frontier.md) | A second provider behind the frontier (Qwen Code), chosen per turn | In progress — ACP backend shipped 2026-09-17 (one adapter for 40+ agents, mirror `aire_agent_log`, E2E on the Mac via `claude-code-acp`); founding consumer waits for the NUC |

## Before #19

The chassis phase — the mirror, the broom, and the first things an owned
database made possible — is closed and archived in
[`00-the-chassis-phase.md`](00-the-chassis-phase.md).
