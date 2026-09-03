# Graceful turn drain — deploys must not kill in-flight turns

Status: **In progress** — paso 1 (retry 502/503) HECHO v4.32.1; el drenaje real
(pasos 2 y 3) sigue SIN construir. Re-verificado 2026-08-06.
Proposed: 2026-07-06 by Claude (Art. 9, receipt del incidente del mismo día)

Verificación 2026-08-06 (Art. 2, receipts):
- `grep -rn "SIGTERM" persona_runner/ persona_gateway/` → el único handler vivo
  está en `persona_runner/workspace_renderer.py` (un loop aparte). Ni el
  `_lifespan` de `persona_runner/runner.py` ni `persona_gateway/boot.py` cierran
  la puerta a turnos nuevos al recibir la señal.
- `az containerapp show -n persona-runner -g insult-rg --query
  properties.template.terminationGracePeriodSeconds` → **`null`** (sigue el
  default de la plataforma; nunca se subió a ~60s).

## What it is
Todo restart de un Container App vivo (`persona-gateway`, `persona-runner`,
`khimeras-host` — el nombre `discord-bot` del receipt original es el app hoy
RETIRADO a 0) mata los turnos EN VUELO: el proceso
recibe SIGTERM y muere a media pipeline, el usuario queda en visto — sin
respuesta y sin siquiera el error in-character de `core/errors.py`. Postgres
resolvió la pérdida de DATOS (2026-05-13); la pérdida del TURNO sigue viva.

**Receipt (2026-07-06 18:30Z):** el flip de `LLM_SHADOW_ROUTER_ENABLED` creó la
rev 0000032; el probe de Bernard ("insult, reporte rápido…", msg
1523757946914345132) tenía `chat_turn_start` 18:30:08 y murió
`outcome=failed:classify_and_analyze` 18:30:22 — la rev nueva levantó 18:30:48.
Visto total. Segundo caso el mismo día: el deploy del CD a las 18:24 también
reinició con tráfico activo.

**Receipt 2 (2026-07-24 01:15Z) — ahora del lado del RUNNER, no del gateway.**
Bernard mencionó a Vultur (msg 1530020509893263390); el turno arrancó 01:14:27 y
a los 48s el `persona-runner` recibió el SIGTERM del rolling update de
`054c909` (cuyo CD había "terminado" 01:14:22):

    agent_runner_turn_failed {"user_text_len": 23723, "elapsed_ms": 48823}
    agent_runner_shutdown_closing_sessions {"count": 1} → agent_runner_stopped
    POST /v1/turn → 502 "agent loop failed: … stop_reason=null"
    persona_gateway_invite_failed  vultur

Dos lecciones nuevas:
1. **El drain hace falta en el runner tanto como en el gateway.** El gateway
   estaba sano; quien murió a media generación fue el proceso del SDK.
2. **Falta un retry en el seam gateway→runner.** Un `502/503` del runner
   significa literalmente "me estoy reiniciando"; un reintento acotado con
   backoff (patrón ya doctrinado en `robustness.md` — jitter, sin circuit
   breaker para un solo upstream) convierte este fallo en un turno tardío en vez
   de un "…". Hoy `PersonaTurnError` va directo al guard.

Nota: el usuario SÍ vio algo — el `dispatch_invite` guard (v4.29.4, mismo día)
mandó el "…" neutral. Antes de ese guard esto habría sido silencio total con el
fallo enterrado en los logs. El guard es la red, no la cura.

**Actualización 2026-09-03 (v4.38.0):** en el camino ruteado por el host el
"…" de la persona ya no existe. El host invoca `/invite` con `wait: true`, lee
el resultado real del turno (`delivered` / `empty` / `failed`), reintenta UNA
vez con la misma persona y, si vuelve a fallar, publica él mismo el aviso con
el nombre de la persona (`demux_ai/fallback.py`). Un 502 del runner que
sobreviva al retry del cliente cae ahora en ese segundo intento del host, no
en un "…". El drenaje (pasos 2-3) sigue pendiente.

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
Parcial: el retry ya está en prod, el DRENAJE no. `personas/insult/bot.py` murió
en la purga — los hosts vivos son `persona_gateway/boot.py`, el `persona_runner`
y (desde el cutover) `khimeras-host`.

Orden sugerido (el retry primero: es 20 líneas y cubre el caso real de hoy):
1. ✅ **HECHO (2026-07-24, v4.32.1)** — Retry 502/503 en
   `khimeras_shared/runner/agent_client.py`. Loop externo (`transient_max_retries=2`)
   que envuelve el connect-retry: un 502/503 (el runner devuelve
   `HTTPException(502, "agent loop failed")` cuando su subprocess SDK muere) se
   re-POSTea con full-jitter backoff (base 0.75s, cap 3s). SOLO 502/503 —
   un 500 es un bug definido (no retry), un 4xx es turno rechazado (no retry),
   un ReadTimeout puede haber landeado (no retry, double-spend). Un 502
   PERSISTENTE agota los reintentos y degrada honestamente vía `RunnerDownError`.
   Tests: `tests/integration/test_agent_client_connect_retry.py`
   (502→retry→éxito, 503→retry→éxito, 502-persistente→RunnerDownError,
   500-no-retry, 4xx-no-retry). Costo aceptado documentado en el código: el
   turno matado pudo gastar tokens antes de morir, así que el retry lo
   double-spendea — aceptable porque el primer gasto no entregó nada y la
   muerte típica por reinicio es `stop_reason=null` (generación nunca completó).
   **El retry convierte el turno perdido en tardío, PERO no cierra el hueco raíz:**
   si el rolling update tarda más que la ventana de retry (~2s), sigue cayendo al
   guard. Los pasos 2-3 (drenaje) son la cura de raíz.
2. **Drain en el runner** (PENDIENTE): dejar de aceptar `/v1/turn` al recibir
   SIGTERM y esperar a las sesiones activas con timeout duro <
   `terminationGracePeriod`.
3. Lo mismo en el gateway + subir `terminationGracePeriodSeconds` en ACA (PENDIENTE).
