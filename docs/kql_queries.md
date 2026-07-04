# KQL Queries — insult-bot prod

Workspace customer ID: `14ebd989-62d2-4207-b099-f6e13256fd72`
Table: `ContainerAppConsoleLogs_CL`
Filter: `ContainerAppName_s == "insult-bot"`
Log string column: `Log_s`

Logs ship as **JSON** when the Container App runs with `LOG_FORMAT=json` (v3.5.9+).
Each `Log_s` is a complete JSON object like
`{"event":"llm_response","model":"claude-sonnet-4-6","output_tokens":22,"stop_reason":"end_turn","timestamp":"..."}`.
Use `parse_json(Log_s)` to pull structured fields. The legacy ANSI-string
queries (using `extract()` regex) stay valid as a fallback when a revision
runs without the env var.

Run via `scripts/kql.sh 'QUERY'` or paste into Azure Portal → Log Analytics workspace → Logs.

## 1. Event rate (pipeline sanity check)

```kql
ContainerAppConsoleLogs_CL
| where TimeGenerated > ago(1h)
| where ContainerAppName_s == "insult-bot"
| summarize count() by bin(TimeGenerated, 5m)
| order by TimeGenerated desc
```

## 2. Reconstruct a single turn by request_id

```kql
ContainerAppConsoleLogs_CL
| where TimeGenerated > ago(6h)
| where ContainerAppName_s == "insult-bot"
| extend p = parse_json(Log_s)
| where tostring(p.request_id) == "<PASTE_ID>"
| project TimeGenerated, event = tostring(p.event), Log_s
| order by TimeGenerated asc
```

## 3. All turns in a time window (diagnose a reported incident)

```kql
ContainerAppConsoleLogs_CL
| where TimeGenerated between(datetime(2026-04-24T03:25:00Z) .. datetime(2026-04-24T03:29:00Z))
| where ContainerAppName_s == "insult-bot"
| extend p = parse_json(Log_s)
| where tostring(p.event) !in ("health_check", "proactive_suppressed", "azure_db_uploaded")
| project TimeGenerated,
    event = tostring(p.event),
    preset = tostring(p.mode),
    pressure = tolong(p.pressure_level),
    tokens_out = tolong(p.output_tokens),
    stop_reason = tostring(p.stop_reason),
    request_id = tostring(p.request_id)
| order by TimeGenerated asc
```

## 4. LLM failures (timeouts, billing, rate limits)

```kql
ContainerAppConsoleLogs_CL
| where TimeGenerated > ago(24h)
| where ContainerAppName_s == "insult-bot"
| extend p = parse_json(Log_s)
| where tostring(p.event) in ("llm_timeout", "llm_failed", "llm_bad_request", "llm_overloaded", "llm_rate_limited", "chat_llm_failed")
| project TimeGenerated,
    event = tostring(p.event),
    error_type = tostring(p.last_error_type),
    error = tostring(p.error),
    attempt = tolong(p.attempt)
| order by TimeGenerated desc
```

## 5. Turns that ended with non-ok outcome

```kql
ContainerAppConsoleLogs_CL
| where TimeGenerated > ago(6h)
| where ContainerAppName_s == "insult-bot"
| extend p = parse_json(Log_s)
| where tostring(p.event) == "chat_turn_end"
| where tostring(p.outcome) != "ok"
| project TimeGenerated,
    outcome = tostring(p.outcome),
    total_ms = tolong(p.total_ms),
    request_id = tostring(p.request_id)
| order by TimeGenerated desc
```

## 6. Preset distribution (drift check)

```kql
ContainerAppConsoleLogs_CL
| where TimeGenerated > ago(24h)
| where ContainerAppName_s == "insult-bot"
| extend p = parse_json(Log_s)
| where tostring(p.event) == "preset_classified"
| summarize count() by preset = tostring(p.mode)
| order by count_ desc
```

## 7. Cache read/create per turn (is prompt caching working?)

```kql
ContainerAppConsoleLogs_CL
| where TimeGenerated > ago(2h)
| where ContainerAppName_s == "insult-bot"
| extend p = parse_json(Log_s)
| where tostring(p.event) == "llm_response"
| project TimeGenerated,
    cache_read = tolong(p.cache_read),
    cache_create = tolong(p.cache_create),
    input_tokens = tolong(p.input_tokens),
    output_tokens = tolong(p.output_tokens),
    stop_reason = tostring(p.stop_reason)
| order by TimeGenerated desc
```

## 8. Delivery failures (Discord HTTP errors)

```kql
ContainerAppConsoleLogs_CL
| where TimeGenerated > ago(24h)
| where ContainerAppName_s == "insult-bot"
| extend p = parse_json(Log_s)
| where tostring(p.event) in ("chat_delivery_failed", "delivery_chunk_failed")
| project TimeGenerated,
    event = tostring(p.event),
    status = tolong(p.status),
    code = tolong(p.code),
    final_text_len = tolong(p.final_text_len),
    error_msg = tostring(p.error_msg)
| order by TimeGenerated desc
```

## 9. Turn latency histogram (detect slow turns)

```kql
ContainerAppConsoleLogs_CL
| where TimeGenerated > ago(24h)
| where ContainerAppName_s == "insult-bot"
| extend p = parse_json(Log_s)
| where tostring(p.event) == "chat_turn_end"
| extend bucket = case(
    tolong(p.total_ms) < 2000, "a:<2s",
    tolong(p.total_ms) < 5000, "b:2-5s",
    tolong(p.total_ms) < 10000, "c:5-10s",
    tolong(p.total_ms) < 30000, "d:10-30s",
    "e:>30s")
| summarize count() by bucket
| order by bucket asc
```

## 10. Find slow LLM calls and what they looked like

```kql
ContainerAppConsoleLogs_CL
| where TimeGenerated > ago(6h)
| where ContainerAppName_s == "insult-bot"
| extend p = parse_json(Log_s)
| where tostring(p.event) == "llm_chat_complete"
| where tolong(p.chat_ms) > 15000
| project TimeGenerated,
    chat_ms = tolong(p.chat_ms),
    raw_text_len = tolong(p.raw_text_len),
    final_text_len = tolong(p.final_text_len),
    text_preview = tostring(p.text_preview),
    model = tostring(p.model),
    exit_reason = tostring(p.exit_reason),
    request_id = tostring(p.request_id)
| order by chat_ms desc
```
