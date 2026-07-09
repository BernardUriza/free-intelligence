#!/usr/bin/env bash
# Progreso de la ventana de medición A.2.3 — router cutover readiness (HOST 5).
#
# WINDOW_START es la activación de discord-bot--0000056 (imagen 7fed455): la
# primera revisión que sirve las tres correcciones juntas — techo de 5s,
# `routed_to_sibling` en vez del mentiroso `diverged`, y cero addressing por
# prefijo. Los logs anteriores usan ConsoleRenderer + el campo viejo, así que
# NO son comparables y no deben mezclarse en esta ventana.
#
# WINDOW_START se puede sobreescribir para validar el instrumento contra un
# rango que SÍ tenga decisiones — un cero solo es creíble si la misma query
# sabe devolver distinto de cero.
#
# Uso: ./scripts/router_window.sh
#      WINDOW_START=2026-07-08T00:00:00Z ./scripts/router_window.sh
set -euo pipefail
cd "$(dirname "$0")/.."

WINDOW_START="${WINDOW_START:-2026-07-09T04:37:37Z}"
TARGET_DECISIONS=50
CEILING_MS=5000

echo "== Ventana A.2.3 — desde ${WINDOW_START} =="
echo

echo "-- Tráfico vs decisiones (un turno sin decisión = router mudo, no 'sin datos') --"
./scripts/kql.sh "
let WINDOW_START = datetime(${WINDOW_START});
ContainerAppConsoleLogs_CL
| where TimeGenerated >= WINDOW_START
| where ContainerAppName_s == 'discord-bot'
| extend ev = tostring(parse_json(Log_s).event)
| where ev == 'chat_turn_start' or ev startswith 'llm_router_cutover'
| summarize n = count() by ev
| order by n desc
"
echo

echo "-- Salud de las decisiones (objetivo: ${TARGET_DECISIONS}; techo: ${CEILING_MS} ms) --"
./scripts/kql.sh "
let WINDOW_START = datetime(${WINDOW_START});
ContainerAppConsoleLogs_CL
| where TimeGenerated >= WINDOW_START
| where ContainerAppName_s == 'discord-bot'
| extend p = parse_json(Log_s)
| where tostring(p.event) == 'llm_router_cutover_decision'
| summarize decisiones = count(),
            a_sibling = countif(tobool(p.routed_to_sibling)),
            p50_ms = percentile(toint(p.latency_ms), 50),
            p95_ms = percentile(toint(p.latency_ms), 95),
            max_ms = max(toint(p.latency_ms)),
            rozan_el_techo = countif(toint(p.latency_ms) > ${CEILING_MS} * 8 / 10)
"
echo

echo "-- Reparto por persona destino --"
./scripts/kql.sh "
let WINDOW_START = datetime(${WINDOW_START});
ContainerAppConsoleLogs_CL
| where TimeGenerated >= WINDOW_START
| where ContainerAppName_s == 'discord-bot'
| extend p = parse_json(Log_s)
| where tostring(p.event) == 'llm_router_cutover_decision'
| summarize n = count() by target = tostring(p.target), reason = tostring(p.reason)
| order by n desc
"
