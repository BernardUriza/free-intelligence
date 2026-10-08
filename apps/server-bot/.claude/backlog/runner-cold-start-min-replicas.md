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

## Medición 2026-10-03 — el tramo de "83 s sin probe" NO es el frío normal

KQL de 30 días (2026-09-03 → 10-03, workspace `14ebd989…`), `ContainerAppSystemLogs_CL`
+ `ContainerAppConsoleLogs_CL`, `ContainerAppName_s == "persona-runner"`. Las
consultas viven en la descripción del PR `feat/runner-startup-probe`. Último arranque
del runner: 2026-09-29 16:43 UTC. Desde que Discord se apagó (09-27) og118 casi no lo
ha despertado.

**Estado vivo (`az containerapp show`, revisión `--0000280`):** `probes: []`,
`minReplicas=0`, `cooldownPeriod=300`, 2 CPU / 4 Gi, grace 600. Sin probes declarados
ACA pone los suyos implícitos (startup TCP period 1 s; readiness TCP period 5 s): 348
de 369 réplicas registran exactamente un `Probe of StartUp failed` antes de que uvicorn
haga bind, y luego pasan.

| Tramo (109 arranques en frío activados por KEDA) | p50 | p90 | máx |
|---|---|---|---|
| asignación → imagen descargada (867 MB, `PulledImage`) | 21 s | 23 s | 28 s |
| asignación → `Uvicorn running` | 28 s | 32 s | 53 s |
| `[entrypoint] booting` → `Uvicorn running` (369 réplicas) | 1 s | 2 s | 7 s |
| lifespan → `turn_pipeline_warm_ready` (n=12) | 13.5 s | 14.4 s | 14.7 s |
| asignación → primer request en la app (n=46 con marcador de inicio) | ~31 s | ~36 s | 71 s |

- El primer request llega **2-4 s después del bind**. El tramo de 83 s del caso fundador
  (09-23 13:32, réplica `--0000240-…-mljps`) no se repite en ningún arranque KEDA de la
  ventana. Ese caso fue atípico también antes del bind (asignación → booting 76 s contra
  27 s normales), y su log de sistema está incompleto (no tiene `PulledImage` ni la
  activación de KEDA), así que su causa sigue **sin identificarse**.
- El costo del frío es **la imagen y el scheduling**: ~21 s de pull de 867 MB más ~6 s
  de asignación. Ningún probe toca eso.
- **Visto desde el gateway** (era del boleto, 09-23 → 09-26, invite `ticket_submitted`
  → runner `ticket_submitted` con el mismo id): 73 turnos, **22 pagaron frío** (espera
  > 20 s; mediana ~38 s, máx 67 s, cero arriba de 120 s). La línea base caliente es ~8 s
  (el gateway arma contexto antes de llamar), así que el frío le costó **~30 s** a cada
  uno de esos 22 turnos.
- `host_turn_gave_up`: 19 en 30 días, **1 después de v4.39.6** (09-26 16:31). Coincidió
  con un arranque, pero lo que lo mató fue un **401 de token OAuth revocado**, no el
  frío. Cero turnos mudos por frío después del alta idempotente. La consulta sí puede
  devolver filas: 343 `host_turn_delivered` en la misma ventana.
- 30 días de arranques: 109 en frío por KEDA (~4/día; 15/día en la semana medida
  originalmente) + 260 réplicas de rollout/deploy.

**Qué se construyó (PR `feat/runner-startup-probe`, v4.47.6, sin aplicar):** probes
declarados en `scripts/cd_runner_template.py`, aplicados por `cd.yml` en el siguiente
deploy del runner: startup HTTP `/health` (¿el proceso arrancó?) y readiness HTTP
`/ready` (503 hasta que `warm_at_boot` termina o vencen los 45 s de `READY_CAP_S`; una
vez en true nunca regresa a 503). El ahorro esperado es **~0 s**, no ~80 s: lo que
cambia es *dónde* espera el primer turno de una réplica fría (en el ingress y no
compitiendo con la carga del modelo). Para og118 (`pipeline=runner`) eso sale tablas,
porque el turno igual esperaba al singleton de MiniLM. Para turnos del gateway
(`pipeline=caller`, no usan embeddings) agrega **hasta ~11 s** de frío cuando Discord
regrese. Hay que revisar ese trade-off antes de reencender el gateway.

**Lo que queda para decidir con datos:** la palanca gratis real no es el probe sino la
**imagen** (867 MB → pull de 21 s). Lo que sigue siendo de Bernard es `min=1` (elimina
los ~30 s del frío y el cache-creation de AIRE).
