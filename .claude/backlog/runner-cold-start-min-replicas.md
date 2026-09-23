# El arranque en frío del runner: `min=0` cuesta un turno mudo al día

Status: Proposed
Proposed: 2026-09-23 by Claude (hallazgo al verificar v4.39.5 en #general)

## What it is

`persona-runner` escala a cero (`minReplicas=0`, `cooldownPeriod=300`, sin
reglas de escala ni probes propios). Cada primer mensaje tras 5 min de silencio
paga un arranque en frío, y ese arranque no es solo el boot del proceso:

| Tramo (2026-09-23, probe 13:32:31 UTC) | Duración |
|---|---|
| summon → `[entrypoint] persona-runner booting` | ~85 s (pull de imagen + scheduling) |
| booting → `Uvicorn running` | ~1.5 s |
| `Uvicorn running` → primer request entregado por el ingress | ~83 s (sin startup probe, ACA espera su propio ciclo) |
| **total summon → alta aceptada** | **169 s** |

En 7 días (KQL 2026-09-16 → 09-23): **105 `agent_runner_starting`** (15
arranques/día) y **5 `host_turn_gave_up`**, cada uno pegado a un arranque. Es
decir: casi todos los arranques caben en el presupuesto, pero ~1 al día no, y ese
es un humano que escribió y recibió "Insult no alcanzó a contestar".

Costos que `min=0` esconde además del turno mudo:
- Cada arranque abre una **sesión AIRE fría** (`aire_route_topic_rolled_over`,
  `cost: the persona system prompt is cache-created again`): cache creation de
  ~90k tokens del prompt de Insult, 15 veces al día.
- Los turnos huérfanos del caso fundador (dos POSTs que el ingress entregó
  cuando ya nadie escuchaba) se pagaron enteros.

## Lo que YA se hizo (v4.39.6, mismo día)

El gateway sobrevive el frío: alta idempotente por `job_id` + reintento del alta
con el mismo id + read timeout del alta de 200 s (`robustness.md` § boleto).
Con eso un frío de hasta ~600 s (presupuesto del turno) ya no mata el mensaje.
Lo que sigue abierto es **cuánto frío se tolera**, no si se sobrevive.

## Canonical path to reuse (Art. 6)

- `persona-gateway` ya documenta `min=1` como requisito de producto en
  `sibling-personas.md` (sobrevivió el sweep de costos del 2026-08-12 con razón
  escrita). Si el runner sube a `min=1`, se documenta igual, en el mismo lugar,
  para que el próximo sweep no "descubra" el ahorro.
- Un **startup probe** HTTP a `/health` en el Dockerfile/CD del runner recorta
  el tramo de 83 s en que ACA espera sin probe (patrón ya usado por el gateway:
  bind→health antes de Discord).

## The decision that's the owner's

1. **`min=1` en `persona-runner`** — 2 CPU / 4 Gi siempre encendidos (~USD
   100+/mes, contra el cache-creation de 15 sesiones frías/día y ~1 turno mudo
   diario). Es gasto: decisión de Bernard, no default.
2. **Startup probe** en el runner — sin costo mensual; recorta ~80 s del frío.
   Reversible y barato; se puede hacer sin `min=1`.
3. Si ninguna: aceptar ~1 primer mensaje lento al día, ya no mudo (v4.39.6).

## Status / next step

Not built. Bernard decide entre 1 y 2 (o ambas). Medición para decidir:
`router_health.py`-style, contar `host_turn_gave_up` por semana después de
v4.39.6 — si cae a cero, el probe basta y `min=1` es solo latencia.

**Re-chequeo 2026-09-23 (tarde):** `az containerapp show -n persona-runner` →
`minReplicas=0`, `terminationGracePeriodSeconds=600` (v4.40.2), revisión
`--0000245` con `d02ae1d`. El boleto durable (v4.40.0–4.40.4) cierra la otra
mitad del daño: un restart del runner a media generación ya no pierde la
respuesta (probado en prod 17:06 UTC, una sola respuesta). Lo que este item
cobra hoy es **sólo latencia** del primer mensaje tras 5 min de silencio, más
el cache-creation de cada sesión AIRE fría. La medición de `host_turn_gave_up`
post-v4.39.6 sigue **sin hacerse** — hacen falta días de ventana, no horas.
