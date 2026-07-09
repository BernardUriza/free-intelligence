# Runbook — Alerts and Probes for insult-bot

This runbook configures the **synthetic monitoring** layer planned in
`.claude/plans/turn_resilience.md` § PR 1. The goal is that the next time
the bot stops processing turns, an alert fires automatically — instead of
the user having to type "se murió otra vez".

For ad-hoc KQL diagnosis queries see `kql_queries.md`.

## What `/debug/health` reports (after PR 1)

```json
{
  "status": "ok",
  "is_ready": true,
  "gateway_latency_ms": 18.4,
  "last_turn_age_s": 42.7,
  "last_turn_within_15min": true,
  "last_turn_outcome": "ok",
  "uptime_s": 4823.1,
  "turns_total": 219
}
```

Field-by-field:

| Field | Meaning | What "bad" looks like |
|---|---|---|
| `status` | Always `"ok"` if the HTTP server is running. Liveness signal. | Endpoint unreachable / non-200. |
| `is_ready` | `bot.is_ready()` from discord.py — gateway connected and READY received. `null` while booting before `on_ready` fires. | `false` for >2 min after boot. |
| `gateway_latency_ms` | Last Discord WebSocket heartbeat latency. `null` until first heartbeat measured. | Above 1000 ms sustained. |
| `last_turn_age_s` | Seconds since `chat_turn_end` was last emitted. `null` until first turn completes. | High during typical activity hours. |
| `last_turn_within_15min` | Convenience boolean — KQL alert and synthetic monitor key on this. | `false` during active hours. |
| `last_turn_outcome` | The outcome of the last turn (`ok`, `llm_failed`, `trivial_skipped`, etc.) — for breaking down "fresh turns" by quality. | Persistent `llm_failed`. |
| `uptime_s` | Process uptime since startup. | Resets unexpectedly = container restart. |
| `turns_total` | Total turns processed since startup. | Stuck on the same value for >15 min during active hours. |

**Always 200.** The endpoint never returns non-2xx. Health interpretation
lives in the monitor (KQL alert, GitHub Action probe), not in the response
code — a 503 here would race Container Apps into restarting a healthy bot
during low-traffic hours.

---

## Layer 1 — Azure Container Apps liveness probe

Probes the bot every 30 s. If the endpoint is unreachable for 90 s
straight, Container Apps restarts the replica.

```bash
az containerapp update \
  --name insult-bot \
  --resource-group insult-rg \
  --liveness-probe-path "/debug/health" \
  --liveness-probe-transport HTTP \
  --liveness-probe-initial-delay-seconds 30 \
  --liveness-probe-period-seconds 30 \
  --liveness-probe-timeout-seconds 5 \
  --liveness-probe-failure-threshold 3
```

**Important:** the probe targets only `status==200`. It does NOT look at
`is_ready` — coupling restart to gateway connectivity would amplify a
short Discord outage into a restart loop. Gateway health is the synthetic
monitor's concern (Layer 3).

Verify after applying:

```bash
az containerapp show \
  --name insult-bot \
  --resource-group insult-rg \
  --query "properties.template.containers[0].probes" -o json
```

---

## Layer 2 — KQL alert: zombie-handler detection

This catches the failure mode that produced the 2026-05-08T23:59 outage:
container is up, gateway latency looks fine, but `on_message` has stopped
processing. The signal is **absence of `chat_turn_end` events** during
expected active hours.

### Query

```kql
ContainerAppConsoleLogs_CL
| where ContainerAppName_s == "insult-bot"
| where TimeGenerated > ago(15m)
| where Log_s contains "chat_turn_end" or Log_s contains "proactive_message_sent"
| count
```

Alert fires when **count == 0** during active-hours window.

### Active-hours definition

Mexico City local time. Outside this window, expect quiet stretches and
do not page:

- Mon–Fri: 09:00–23:00 MX (15:00–05:00 UTC)
- Sat–Sun: 11:00–23:00 MX (17:00–05:00 UTC)

In KQL, restrict the alert query window using `datetime_local_to_utc()` or
filter by `dayofweek(TimeGenerated)` + `hourofday(TimeGenerated)` (UTC).

## The three alert rules that actually exist (verified 2026-07-08)

Print them, never trust this list: `./scripts/dr_inventory.sh`.

| Rule | Sev | Every | Fires when |
|---|---|---|---|
| `insult-canary-heartbeat-absent` | 1 | 30m | zero `canary_probe_ok` in 150m |
| `insult-turn-failure-rate` | 2 | 15m | ≥3 failed turns / router timeouts / gateway failures in 30m |
| `invite-accepted-without-completion` | 1 | 15m | an invite was accepted but no persona turn completed |

All three route to action group `prod-trust-ag` → bernarduriza@gmail.com.

### The 2026-07-08 incident: all three were dead, two of them silently

Discovered while measuring the router cutover. Two independent faults, stacked:

1. **Wrong workspace.** All three had `scopes` pointing at
   `workspace-insultrgA7Kz` (`a07bf4c8-…`), which has been FROZEN since the
   2026-06-25 billing incident. They were querying a dead workspace.
2. **`has` instead of `contains`.** Their predicates (`Log_s has 'chat_turn_end'`,
   `has 'outcome=failed'`, `has 'llm_router_cutover_failed'`) match **zero rows**
   — see `docs/kql_queries.md` § traps. `insult-turn-failure-rate` could not have
   fired if every turn in production had failed.

The canary rule was the nastiest: it fires on `ok_count == 0`, and a dead
workspace always yields zero, so it sat **Fired since 2026-07-08T01:42** — a false
positive for 25h while the canary was healthy. With `autoMitigate` it would not
have re-notified, so a *real* canary death would have produced **no new signal**.
An alert stuck Fired is worse than no alert.

**Fix:** Azure refuses `scopes` updates on a scheduled query rule
(`BadRequest: Scope can not be updated`), so all three were **deleted and
recreated** in `eastus2` against the live workspace, with `contains` predicates
validated against real rows first (7 real failures / 3 real canary heartbeats).

**Lesson:** an alert that has never fired is not evidence of health. Before
trusting one, run its query by hand and confirm it returns the rows you expect on
a window where you KNOW the bad thing happened.

### Provisioning the alert (Portal — manual today, IaC later)

1. Azure Portal → Log Analytics workspace
   `14ebd989-62d2-4207-b099-f6e13256fd72` → **Alerts** → **+ Create**
2. Condition: **Custom log search**, paste the query above, set
   threshold = `0`, evaluation frequency `5m`, lookback `15m`.
3. Action group: email + webhook. Severity 2 (Warning).
4. Suppress during off-hours via the schedule UI (or extend the query
   with a `where hourofday(...)` filter to short-circuit to a
   non-zero count outside active hours).

### How to test the alert without breaking prod

In a low-traffic window, manually scale the Container App to 0 replicas
for 16 minutes:

```bash
az containerapp update -n insult-bot -g insult-rg --min-replicas 0 --max-replicas 0
# wait 16 min
az containerapp update -n insult-bot -g insult-rg --min-replicas 1 --max-replicas 1
```

The alert should fire. If it doesn't, check the Portal alert history for
"Could not evaluate" errors (usually permissions or quoting).

---

## Layer 3 — Synthetic E2E probe (GitHub Action, deferred)

Configures a dummy Discord account to send a `!ping` to a dedicated
`#bot-health` channel every 60 minutes and assert a bot reply within
30 s. Not implemented yet — requires:

1. **`#bot-health` channel** created in the test guild with restricted
   permissions (only the dummy account and the bot).
2. **Dummy bot account** with its own `DISCORD_BOT_TOKEN`, added to the
   guild and to `#bot-health` only.
3. **GitHub repository secrets**: `SYNTHETIC_PROBE_BOT_TOKEN`,
   `SYNTHETIC_PROBE_GUILD_ID`, `SYNTHETIC_PROBE_CHANNEL_ID`.

Skeleton workflow when the prerequisites are in place:

```yaml
# .github/workflows/synthetic_probe.yml
name: Synthetic Probe
on:
  schedule:
    - cron: "0 * * * *"  # hourly
  workflow_dispatch:
jobs:
  probe:
    runs-on: ubuntu-latest
    timeout-minutes: 3
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.14" }
      - run: pip install discord.py
      - env:
          DISCORD_BOT_TOKEN: ${{ secrets.SYNTHETIC_PROBE_BOT_TOKEN }}
          GUILD_ID: ${{ secrets.SYNTHETIC_PROBE_GUILD_ID }}
          CHANNEL_ID: ${{ secrets.SYNTHETIC_PROBE_CHANNEL_ID }}
        run: python scripts/synthetic_probe.py
```

The probe script (not yet written) connects, posts `!ping`, waits up to
30 s for a reply from `INSULT_BOT_USER_ID`, exits non-zero if no reply.

Until this is wired, **Layer 2 (KQL alert) is the only autonomous
detection**. Layer 2 alone is sufficient for the failure modes seen so
far; Layer 3 is added when we want to detect "bot answers but answer is
broken" (e.g., empty body, character break in 100% of responses). That
class of bug is rarer and Layer 2 already catches all cases of "bot
silent".

---

## Layer 4 — Manual `curl` smoke test

Always available as the last resort. The endpoint is publicly reachable
(Container App ingress) but bearer-token gated for non-`/debug/health`
paths.

```bash
curl -s "https://insult-bot.nicecliff-10074f57.eastus.azurecontainerapps.io/debug/health" | jq
```

If the response is missing `is_ready`, `last_turn_age_s`, or
`last_turn_within_15min`, the deploy is pre-PR1 and the synthetic
monitoring layer is not yet present.

---

## Decision flow when an alert fires

1. **Layer 2 alert fires** (no `chat_turn_end` in 15 min during active
   hours).
2. Hit Layer 4 first: `curl /debug/health`. Three branches:
   - **Endpoint unreachable** → container restart loop, ingress issue,
     or DNS. Check `az containerapp show ... --query
     properties.runningStatus` and recent revisions.
   - **`status=ok`, `is_ready=false`** → gateway disconnected. Check KQL
     for `bot_disconnected` events without `bot_resumed`.
   - **`status=ok`, `is_ready=true`, `last_turn_age_s` huge** → zombie
     handler. The exact failure mode of 2026-05-08T23:59. Pull KQL for
     the last 30 minutes of `chat_llm_failed`, `chat_turn_failed`, and
     `discord_typing_throttled` events to find the stuck stage.
3. **Restart the replica** as the last resort:
   `az containerapp revision restart --name insult-bot -g insult-rg
   --revision <name>`. Always investigate before restarting in
   production — the restart hides the evidence.
