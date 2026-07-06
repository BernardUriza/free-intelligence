# Graceful turn drain — deploys must not kill in-flight turns

Status: Proposed
Proposed: 2026-07-06 by Claude (Art. 9, receipt del incidente del mismo día)

## What it is
Todo restart del Container App `discord-bot` (deploy del CD, `az containerapp
update` de un env var, revision swap) mata los turnos EN VUELO: el proceso
recibe SIGTERM y muere a media pipeline, el usuario queda en visto — sin
respuesta y sin siquiera el error in-character de `core/errors.py`. Postgres
resolvió la pérdida de DATOS (2026-05-13); la pérdida del TURNO sigue viva.

**Receipt (2026-07-06 18:30Z):** el flip de `LLM_SHADOW_ROUTER_ENABLED` creó la
rev 0000032; el probe de Bernard ("insult, reporte rápido…", msg
1523757946914345132) tenía `chat_turn_start` 18:30:08 y murió
`outcome=failed:classify_and_analyze` 18:30:22 — la rev nueva levantó 18:30:48.
Visto total. Segundo caso el mismo día: el deploy del CD a las 18:24 también
reinició con tráfico activo.

## Canonical path to reuse (Art. 6)
El signal handling ya existe (`bot.py`: SIGTERM/SIGINT → graceful shutdown que
cierra DB y bot). El drain se cuelga AHÍ: al recibir SIGTERM, (1) dejar de
aceptar mensajes nuevos (el gate de `handle_incoming` se cierra), (2) esperar a
que los turnos activos terminen (con timeout duro ~30s < terminationGracePeriod
del Container App), (3) recién entonces cerrar. Si el timeout vence, mandar el
error in-character antes de morir. Complemento opcional: ACA soporta
`terminationGracePeriodSeconds` en el template — subirlo a ~60s.

## The decision that's the owner's
Si además se quiere re-encolar el turno matado (releer el mensaje al arrancar
la rev nueva y responderlo tarde) o solo drenar limpio. Drenar limpio es el 90%
del valor con 10% del riesgo; el replay cruza con dedup (`_processed`).

## Status / next step
No construido. Siguiente paso: slice en `personas/insult/bot.py` — flag de
draining + contador de turnos activos + wait-with-timeout en el shutdown
handler, con test que simule SIGTERM a media pipeline.
