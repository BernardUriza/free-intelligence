# Graceful turn drain — deploys must not kill in-flight turns

Status: **Done** (2026-09-22) — pasos 1, 3 y 2' HECHOS. El grace period del
gateway está en 45 s (revisión `persona-gateway--0000224`) y declarado en `cd.yml`.
Proposed: 2026-07-06 by Claude (Art. 9, receipt del incidente del mismo día)

## Corrección 2026-09-09 — dos cosas que este documento decía mal

Auditoría con recibos, disparada por una revisión del backlog. **Ejecutar los
pasos 2 y 3 tal como estaban escritos habría construido lo que ya existe y
habría metido un bug de respuestas duplicadas.**

**1. El runner YA drena. La premisa del paso 2 era falsa.** `entrypoint.sh:49`
hace `exec uvicorn`, y uvicorn instala su propio handler de SIGTERM
(`Server.capture_signals`); su `shutdown()` cierra el socket de escucha y luego
espera a las requests en vuelo con `timeout_graceful_shutdown`, cuyo default es
`None` — **espera indefinida**. Un `/v1/turn` en vuelo no lo corta el SIGTERM:
lo corta el SIGKILL de la plataforma al vencer el grace period. Así que el
trabajo del runner no es *construir* un drain, es **darle tiempo al que ya
tiene**: subir `terminationGracePeriodSeconds`. Lo que sí rompe es el turno
NUEVO, que pega contra el socket ya cerrado — y eso es el paso 1, no el 2.

**2. Subir el grace period en el GATEWAY, sin gate de recepción, produce
respuestas DOBLES.** El gateway sostiene el websocket de Discord de cada
persona. Con un grace largo, la réplica vieja mantiene su sesión conectada
mientras la nueva ya conectó: dos réplicas con el mismo token, y el usuario ve
cada respuesta dos veces. Ahí el gate de recepción **es prerequisito del grace
period, no un complemento opcional** como decía la sección "Canonical path".
Matiz: uvicorn en el gateway (`app.py:100/103`) ya drena los `/invite` con
`wait:true`; lo que no se drena son los turnos por mención (`on_message`) y los
`wait:false`, que salen por `create_task`.

**No verificado:** el default real del grace period en Container Apps y si la
plataforma manda SIGKILL al vencerlo. No se leyó de la doc ni se observó un
deploy con un turno en vuelo; se infiere del comportamiento. **Eso hay que
medirlo antes de tocar el grace period**, porque es el número que decide todo lo
demás.

Re-chequeo 2026-09-07 (Art. 2, receipts):
- `az containerapp show -n persona-runner -g insult-rg --query
  properties.template.terminationGracePeriodSeconds -o tsv` → vacío (**`null`**);
  lo mismo para `persona-gateway` → **`null`**. Nadie subió el grace period.
- `grep -rn -i "sigterm\|add_signal_handler" persona_runner/ persona_gateway/
  --include='*.py'` → el único handler sigue en
  `persona_runner/workspace_renderer.py:247` (loop aparte). El `_lifespan` de
  `persona_runner/runner.py:38` sólo cierra clientes (`aire_route.py:330`), no
  cierra la puerta a turnos nuevos.
- **El objeto del drain cambió de forma** con el borrado de la etapa 2
  (`fc0944a`, v4.35.0, 2026-08-28): el runner ya no hosteda un subprocess del
  SDK — un SIGTERM a media generación hoy corta una request `httpx` a la puerta
  de AIRE. Los pasos 2-3 siguen siendo los mismos (dejar de aceptar `/v1/turn`,
  esperar las requests en vuelo, subir el grace period), pero el "esperar
  sesiones activas" ahora es esperar requests HTTP, no procesos Node.
- La actualización del 09-03 de abajo (`e09f979`, v4.38.0) sigue vigente y es
  red, no cura: el host reintenta UNA vez y habla por la casa; un rolling update
  más largo que ese retry sigue matando el turno.

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
error in-character antes de morir.

**Corregido 2026-09-09:** subir `terminationGracePeriodSeconds` NO es un
"complemento opcional". En el runner es la pieza que falta (su drain ya existe,
lo que le falta es tiempo) y en el gateway es lo que NO se puede tocar antes del
gate, porque produce dos réplicas sobre el mismo token de Discord. La frase
original invitaba a hacerlo suelto y por eso se corrige aquí.

**Actualización 2026-09-10 (v4.38.30):** el gate ya está construido
(`persona_gateway/drain.py` + `ShutdownController`), así que la condición que
bloqueaba el grace period del gateway está cumplida. Ver el paso 3 abajo.

## The decision that's the owner's
Si además se quiere re-encolar el turno matado (releer el mensaje al arrancar
la rev nueva y responderlo tarde) o solo drenar limpio. Drenar limpio es el 90%
del valor con 10% del riesgo; el replay cruza con dedup (`_processed`).

## Status / next step
**Cerrado 2026-09-22.** El retry (1) y el gate de recepción (3) están hechos y
desplegados (v4.38.46 arregló el crash de arranque del gate), y el paso 2' se
aplicó: `terminationGracePeriodSeconds` era `null` (default 30) y quedó en **45**
en `persona-gateway` (`az containerapp update --termination-grace-period 45`,
revisión resultante `persona-gateway--0000224`, `show` devuelve 45). El CD lo
repite en cada deploy del gateway (`cd.yml`, paso "Deploy persona-gateway"), así
un `update --image` nunca lo pisa. Sigue abierto como MEDICIÓN, no como bloqueo:
el p95 de `elapsed_ms` para confirmar que 25 s de drenaje alcanzan; si sube,
suben los dos manteniendo grace ≥ drain + 20 s.

**Actualización 2026-09-19 (v4.39.0) — el gate estaba desplegado y NO corrió.**
Receipt: msg 1550695386153488405 en #general. El deploy de v4.38.48 mandó **dos
SIGTERM a 0.1 ms** (`persona_gateway_shutdown_signal inflight=1` y
`persona_gateway_shutdown_forced` en el mismo milisegundo). El handler leía la
segunda señal como "ya, mátalo", así que el drenaje jamás arrancó y el turno
vivo (el reintento del host sobre Vultur) murió en el acto. Arreglado en
`ShutdownController.__call__`: un SIGTERM repetido se loguea
(`persona_gateway_shutdown_signal_repeat`) y se ignora; solo un **segundo SIGINT**
fuerza, como uvicorn. Un drenaje colgado no queda inmortal: SIGKILL al vencer el
grace period. Test: `test_a_repeated_sigterm_is_ignored_and_the_drain_keeps_running`.

Y lo que ese incidente destapó NO era de este item: el turno ya estaba perdido
seis minutos antes del SIGTERM, porque **el ingress corta toda request a los
240 s** y el turno tardó 326.9 s. Eso vive en `robustness.md` § *Un turno NUNCA
viaja en una sola request* — turnos con boleto en las dos costuras.

**Nota para el paso 2':** el drenaje del gateway (`drain_timeout_s=25`) no cubre
un turno de 5 minutos, y no debe: el grace period de la plataforma es el techo
real. Cuando se mida, el número a comparar es `first_turn_timeout_s` (600 s),
no los 25 s del drain.

Historial: el retry ya está en prod, el DRENAJE no lo estaba. `personas/insult/bot.py` murió
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
   guard.
   **AMPLIADO 2026-09-09 (v4.38.22):** la mitad de *connect* del paso 1 estaba
   mal dimensionada y era la que más dolía. Un turno nuevo durante el swap recibe
   `ConnectError` contra el socket ya cerrado, y la política vieja (2 reintentos,
   base 0.25s) gastaba **0.75s** antes de declarar el cerebro muerto — contra un
   rolling update que dura decenas de segundos y un runner que además arranca en
   frío (`min=0`). El presupuesto ahora es un **reloj**, no un contador:
   `connect_budget_s=45`, con tope duro de 8 reintentos y backoff topado a 8s
   (~32s de cobertura). Reintentar el connect es provablemente seguro —el cuerpo
   nunca se envió— así que esto no arriesga double-spend, a diferencia del loop
   de 502/503. El log de agotamiento ahora dice **cuál** límite se acabó
   (`gave_up_on=budget|attempts`): quedarse sin intentos es "no hay nadie
   escuchando", quedarse sin presupuesto es "cuelga" — un runner saturado y uno
   ausente dejaron de leerse igual. Tests: los dos de arriba más
   `test_connect_budget_covers_a_rolling_update` y
   `test_el_presupuesto_de_reloj_corta_antes_que_los_intentos` (resistencia: un
   connect que cuelga no puede vivir más que el presupuesto). Ambos verificados
   en rojo con el corte saboteado antes de darlos por buenos.
2. **~~Drain en el runner~~ → medir el grace period y subirlo** (HECHO 2026-09-22, ver 2').
   Ver la corrección de arriba: el drain ya lo hace uvicorn y espera
   indefinidamente. Lo que falta es que la plataforma le dé tiempo. Primer paso
   real: **medir** el default de `terminationGracePeriodSeconds` en Container
   Apps y confirmar qué manda al vencer, en vez de inferirlo.
3. ✅ **HECHO (2026-09-10, v4.38.30) — Gate de recepción en el gateway.**
   `persona_gateway/drain.py::TurnGate` es un ledger de turnos en vuelo con una
   puerta que se cierra una sola vez. Los DOS puntos de entrada guardados piden
   ficha antes de trabajar y la devuelven en un `finally`:
   `PersonaClient._dispatch` (la @mención y el edit-summon) y
   `PersonaClient.dispatch_invite` (el camino del host, con y sin `wait`, y el
   `[INVITE:]` de un hermano). El gate es UNO por proceso — `_main` lo construye
   y lo inyecta en las N personas, porque el SIGTERM llega una sola vez.

   `persona_gateway/app.py::ShutdownController` es el dueño de SIGTERM/SIGINT
   (`loop.add_signal_handler`): cierra la puerta, marca `boot.stopping`, espera a
   los vivos con tope duro `CONFIG.drain_timeout_s` (**25s**, env
   `DRAIN_TIMEOUT_S`), y recién entonces baja uvicorn (`should_exit`) y cierra
   cada sesión de Discord. Un turno rechazado **no manda "…"**: no falló, esta
   réplica ya no recibe; el host lee `failed`, reintenta una vez
   (`demux_ai/fallback.py`) y ese retry aterriza en la réplica nueva.

   Tres detalles que son parte del entregable, no adorno:
   - **A uvicorn se le quita su handler** (`install_signal_handlers=False`) sólo
     cuando el gateway logró instalar el suyo — los dos usan `signal.signal` y el
     último gana, así que dos dueños de la misma señal es un dueño indefinido. Si
     la instalación falla, uvicorn conserva los suyos y el cierre es el de hoy.
   - **El abandono se cuenta**: vencido el tope, `drain` devuelve QUIÉNES quedaron
     vivos y el controller emite `persona_gateway_drain_abandoned`
     (`abandoned=N, turns=[...], timeout_s`). Un abandono silencioso es peor que
     uno contado. KQL: ese evento + `persona_gateway_turn_refused_draining`.
   - **Fail-safe en las dos direcciones**: un drenaje que revienta se loguea y se
     sigue al cierre; una segunda señal restaura el handler por default y mata sin
     preguntar. La falla que esto previene (turnos cortados) es más barata que la
     que podría introducir (un proceso que no cierra).

   `/health` ahora reporta `stopping`, y la salida ordenada de cada persona deja
   de loguearse con los mismos eventos de error que su muerte imprevista
   (`persona_gateway_persona_drained` / `persona_gateway_stopped`).

   Arnés: `tests/core/test_gateway_turn_gate.py` (15 casos). Los tres que
   importan, **verificados en rojo saboteando el fix** antes de darlos por buenos:
   (a) `admit` sin mirar `_accepting` → rojo en los 3 tests de "no entra trabajo
   nuevo"; (b) `drain` que no espera → rojo en resistencia, exactamente en
   `closed.assert_not_awaited()` (la sesión del turno vivo se cerraba debajo);
   (c) el abandono tragado en silencio, y un `drain` que miente y devuelve `[]`
   al vencer → rojo en los dos tests del tope duro.

2'. **Medir el grace period y subirlo — APLICADO 2026-09-22: 45 s en `persona-gateway`, revisión `persona-gateway--0000224`; declarado en `cd.yml`.**
   Con el gate puesto, subirlo ya no produce respuestas dobles: la réplica vieja
   conserva su websocket pero **no recibe**, así que los eventos que le llegan los
   ignora. Sigue sin medirse lo que decide el número: el default real de
   `terminationGracePeriodSeconds` en Container Apps y qué manda la plataforma al
   vencerlo (hoy es `null` en las tres apps, verificado con `az`; el campo SÍ
   existe en el schema del template).

   **Número propuesto: `terminationGracePeriodSeconds: 45` en `persona-gateway`.**
   El razonamiento, para que se pueda discutir en vez de creerse: 25s de drenaje
   (el tope duro) + ~20s de margen para el cierre del websocket de Discord, la
   salida de uvicorn y el cierre del pool de Postgres. La invariante que hay que
   preservar si alguno de los dos se toca es **grace ≥ drain + 20s**; si el grace
   queda por debajo del drenaje, la plataforma manda SIGKILL a media espera y el
   gate no compra nada.

   Lo que sí falta medir antes de fijarlo: **el p95 de duración de turno** (el
   `elapsed_ms` de los turnos en KQL). 25s es un techo conservador elegido para
   que el cierre completo quepa cómodo bajo 45s, no un número medido. Si el p95
   resulta mayor, los dos suben juntos manteniendo la invariante — nunca el grace
   solo, nunca el drenaje solo.

   En el **runner** el trabajo es distinto y más simple: su drain ya existe
   (uvicorn espera indefinidamente), así que ahí subir el grace period es TODO el
   trabajo. No necesita gate: no sostiene ningún websocket de Discord, así que
   una réplica vieja viva no puede contestar dos veces.
