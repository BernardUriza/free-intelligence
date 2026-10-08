# Fase B — reanudar un turno del runner por REATTACH a AIRE, no re-preguntando

Status: Proposed — lado server-bot hecho hasta donde AIRE lo permite (v4.40.23); bloqueado en aire-server + fi-runner
Proposed: 2026-09-23 by Claude (plan "que las respuestas siempre lleguen", slice 5)

## What it is

Con v4.40.2 el runner tiene un boleto durable (`turn_jobs`): si muere a media
generación, la réplica siguiente reclama la fila y **re-corre** el turno bajo el
mismo `job_id`. Eso salva la respuesta, pero le manda a AIRE el mismo mensaje del
usuario **dos veces** al mismo topic — en el caso (c) del stress-test (AIRE ya
había guardado usuario y respuesta cuando el runner murió) el modelo ve su propia
respuesta y la misma pregunta. Se mitiga con `TurnRequest.resumed`
(`needs_fold=False` + `prompts_md/turn_resume_note.md`), no se cierra.

La forma correcta es que el turno de AIRE **sobreviva al runner** y que la
réplica nueva se **reenganche** al resultado en vez de re-preguntar.

## Lo que ya existe del otro lado (verificado 2026-09-23, sólo lectura)

- aire-server `server/aire/messages.py:50-58`: `POST /projects/{p}/sessions/{s}/messages`
  acepta `background: true` → arranca un turno **desacoplado del socket**
  (`engine/detach.py`), 409 si ya corre uno en esa sesión (`engine/core.py:91-95`).
  Status en `GET …/status` (:84-90); `GET …/sessions/{s}` → `{exists}` (:93).
- El POST **no tiene idempotency key**; el transcript se deduplica por el `uuid`
  de cada entrada del SDK (`store.py:175, 188-193, 230`), no por una clave del cliente.
- fi-runner 0.21.7 (`fi_runner/backends/aire.py:304-336, 423-436`): manda
  `{mode, message, tools?, remote_tools?, model?, images?}` — **ni `background`
  ni ningún id de turno**. `has_durable_memory` (:357-370) confirma que AIRE es
  la memoria.

## Canonical path to reuse (Art. 6)

1. **aire-server:** aceptar un `turn_id` (idempotency key) en el POST de
   messages; con `background:true` devolver el id y exponer el **resultado**
   (no sólo el status) en `GET …/status` o un `GET …/turns/{turn_id}`.
2. **fi-runner (`AIREBackend`):** opción `background=True` + `reattach(turn_id)`
   que pollea el status y devuelve el `TurnResult` completo (texto, usage,
   model). Release al canal conda (`bernardurizaorozco`) y bump del pin aquí.
3. **server-bot runner:** `turn_jobs` ya guarda `aire_sent_at`; añadir
   `aire_turn_id`. En `_resumer`, si la fila trae `aire_turn_id` → `reattach`
   en vez de `runner(req, resumed=True)`; sólo si el reattach dice "no existe"
   se re-pregunta. Quitar entonces la nota de reintento del camino reattach.

## The decision that's the owner's

Es trabajo cross-repo (aire-server + free-intelligence + aquí) con un release de
fi-runner en medio. Bernard decide cuándo entra; hasta entonces la fase A es
honesta por escrito: reanudar = re-preguntar.

## Re-verificado 2026-09-25 (sólo lectura de aire-server + fi-runner instalado)

Las afirmaciones de arriba se sostienen, y el hueco es MÁS grande de lo que dice
el punto 1. Lo que falta del lado de AIRE no es sólo la idempotency key:

- `POST …/messages` con `background:true` responde `{"status":"accepted","session":…}`
  (`messages.py::_launch_background`): **ningún id de turno**.
- El resultado de un turno desacoplado **se tira**: `engine/detach.py::drain_detached`
  consume el stream sólo para cobrar (`on_cost`) e imprimir errores. El texto no
  queda en ningún lugar que la puerta sirva. `GET …/status` devuelve
  `{"running": bool}` y **nada más**.
- `GET …/status` mira SÓLO `engine.detached` (las tasks lanzadas con
  `background`). Para un turno por SSE —que es como mandamos todos hoy— responde
  `running:false` siempre: consultarlo al reanudar sería un check que no puede
  fallar. Por eso **no** se cableó aquí.
- No hay superficie HTTP para leer el transcript (daemon write-only); el runner no
  tiene ni debe tener la credencial del Postgres del droplet.
- fi-runner 0.21.7 (`backends/aire.py`, el pin actual) manda
  `{mode, message, tools?, remote_tools?, model?, images?}`: sin `background` ni id.

**Conclusión honesta:** el reattach NO se puede hacer desde server-bot. Mandar
`background:true` a mano (saltándose `AIREBackend`) lanzaría un turno cuya
respuesta nadie puede leer — peor que la fase A. No se simula detrás de un flag.

## Lo que SÍ se hizo en server-bot (v4.40.23)

El paso 3 decía "`turn_jobs` ya guarda `aire_sent_at`". Lo guardaba y **nadie lo
leía**: `row.extra["aire_sent"]` viajaba en la fila sin consumidor, y la
reanudación marcaba `resumed=True` SIEMPRE. Un job que murió ANTES de cruzar a
AIRE (topic claim, ruteo, facts) se reanudaba como "reintento": sin historia
plegada en un tópico nuevo y con la nota de "puede que ya hayas contestado" sobre
un mensaje que AIRE nunca vio.

- `turn_jobs.crossed_to_aire(row)` decide: cruzó → fase A (`resumed=True`, sin
  pliegue, con nota); no cruzó → turno nuevo (`resumed=False`) +
  `agent_runner_job_resumed_before_aire`. Una fila sin el dato se lee como
  cruzada (equivocarse hacia ahí cuesta una nota; hacia el otro, pliega la
  historia dos veces).
- Consecuencia medible: **cada `aire_route_turn_resumed` en KQL es ahora
  exactamente un mensaje del usuario duplicado en el transcript de AIRE** — la
  cifra que la fase B tiene que llevar a cero. Antes el evento mezclaba los dos
  casos.
- Tests: `tests/agent/test_turn_jobs_api.py` (positiva: murió antes de AIRE →
  turno limpio; resistencia: fila sin dato → contrato fase A) +
  `tests/agent/test_runner_shutdown.py` (la reanudación en boot de un job que
  cruzó sigue marcando `resumed`).
- **v4.47.3 (al traer `main` post-F3):** `resumed` dejó de cargar dos
  significados. Lo que AIRE vio sigue en `resumed`; lo que ya está en `messages`
  va en `TurnRequest.ask_stored`, que el runner pone en TODO job reanudado. Sin
  eso, un job `pipeline="runner"` (og118) que murió armando el contexto —antes
  de AIRE pero DESPUÉS de `_store_ask`— guardaba la pregunta dos veces. Y la
  reanudación del arranque entraba directo a `turn_via_aire`, saltándose la
  tubería entera (contexto, guía, guardado de la respuesta); ahora entra por
  `serve_turn`. Tests: `tests/agent/test_turn_jobs_pipeline_resume.py`.
- Residual conocido: `mark_aire_sent` es best-effort; si Postgres falla en ESE
  update y vuelve para la reanudación, la fila dice "no cruzó" y se re-pliega la
  historia. Ventana estrecha (Postgres caído justo en esa sentencia); aceptada.

## Lo que falta, por repo (en orden)

1. **aire-server** (sin item propio todavía; el #22 cerró 22a/22b sin esto):
   aceptar `turn_id` en el POST de messages (dedupe: el mismo id con un turno
   vivo o terminado NO relanza), y conservar el **resultado** del turno
   desacoplado (texto/answer, usage, model, subtype) servido por
   `GET …/turns/{turn_id}` o en `…/status`, con TTL. Mientras `drain_detached`
   tire el texto, no hay nada a qué reengancharse.
2. **fi-runner (`AIREBackend`)**: `run_turn(..., background=True, turn_id=…)` +
   `reattach(turn_id) -> TurnResult | None` (None = AIRE no lo conoce). Release al
   canal conda y bump del pin en `environment.yml`.
3. **server-bot**: mandar `turn_id = job_id` en cada turno; en `_resumer`, si
   `crossed_to_aire(row)` → `reattach(job_id)` antes de re-preguntar; sólo si
   devuelve None se cae a la fase A. Quitar la nota de reintento del camino
   reattach. El gate ya está en su lugar: es la misma rama de `crossed_to_aire`.

## Status / next step

Server-bot foundation built (v4.40.23): la reanudación ya distingue "cruzó a
AIRE" de "no cruzó", y `aire_route_turn_resumed` cuenta sólo duplicados reales.
El reattach sigue bloqueado por aire-server (resultado + turn_id) y fi-runner. Recibo para arrancar: un restart del runner a media generación
(`az containerapp revision restart`) con `aire_route_turn_resumed` en KQL y UNA
sola respuesta en #general — ése es el estado actual; la fase B se mide por que
`aire_route_turn_resumed` deje de mandar un segundo mensaje al transcript de AIRE.
