#!/usr/bin/env bash
# Progreso de la ventana de medición A.2.3 — salud del router del host (HOST 5/6).
#
# Era post-cutover (2026-07-15, v4.22.68 c941003): el router vive en el
# Container App `khimeras-host` (DirectAzureLLMRouter, gpt-4.1). Los emisores
# reales son:
#   host_router_llm_response   → cada decisión LLM (model, latency_ms, tokens)
#   host_router_llm_error      → fallo del backend LLM
#   host_dispatched            → dispatch a persona (target, accepted, reason)
#   host_mention_shortcircuit  → mención directa (NO cuenta como decisión LLM)
#   host_dispatch_router_failed / host_dispatch_no_target → router mudo
#
# La versión anterior de este script medía `llm_router_cutover_decision` en el
# app RETIRADO `discord-bot` — cero eterno post-castigo. Un cero solo es
# creíble si la misma query sabe devolver distinto de cero: valida el
# instrumento con la sección de tráfico (host_dispatched debe verse cuando
# hubo turnos en #general).
#
# Uso: ./scripts/router_window.sh
#      WINDOW_START=2026-07-15T00:00:00Z ./scripts/router_window.sh
set -euo pipefail
cd "$(dirname "$0")/.."

WINDOW_START="${WINDOW_START:-2026-07-15T00:00:00Z}"
TARGET_DECISIONS=50
CEILING_MS=5000

echo "== Ventana A.2.3 (era host) — desde ${WINDOW_START} =="
echo

echo "-- Tráfico del host: decisiones vs shortcircuits vs fallos --"
./scripts/kql.sh "
let WINDOW_START = datetime(${WINDOW_START});
ContainerAppConsoleLogs_CL
| where TimeGenerated >= WINDOW_START
| where ContainerAppName_s == 'khimeras-host'
| extend ev = tostring(parse_json(Log_s).event)
| where ev in ('host_router_llm_response', 'host_router_llm_error', 'host_dispatched', 'host_mention_shortcircuit', 'host_dispatch_router_failed', 'host_dispatch_no_target')
| summarize n = count() by ev
| order by n desc
"
echo

echo "-- Salud de las decisiones LLM (objetivo: ${TARGET_DECISIONS}; techo: ${CEILING_MS} ms) --"
./scripts/kql.sh "
let WINDOW_START = datetime(${WINDOW_START});
ContainerAppConsoleLogs_CL
| where TimeGenerated >= WINDOW_START
| where ContainerAppName_s == 'khimeras-host'
| extend p = parse_json(Log_s)
| where tostring(p.event) == 'host_router_llm_response'
| summarize decisiones = count(),
            p50_ms = percentile(toint(p.latency_ms), 50),
            p95_ms = percentile(toint(p.latency_ms), 95),
            max_ms = max(toint(p.latency_ms)),
            rozan_el_techo = countif(toint(p.latency_ms) > ${CEILING_MS} * 8 / 10)
"
echo

echo "-- Reparto por persona destino (host_dispatched) --"
./scripts/kql.sh "
let WINDOW_START = datetime(${WINDOW_START});
ContainerAppConsoleLogs_CL
| where TimeGenerated >= WINDOW_START
| where ContainerAppName_s == 'khimeras-host'
| extend p = parse_json(Log_s)
| where tostring(p.event) == 'host_dispatched'
| summarize n = count(), aceptados = countif(tobool(p.accepted)) by target = tostring(p.target)
| order by n desc
"
