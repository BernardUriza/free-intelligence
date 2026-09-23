# Fase B — reanudar un turno del runner por REATTACH a AIRE, no re-preguntando

Status: Proposed
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
3. **discord-bot runner:** `turn_jobs` ya guarda `aire_sent_at`; añadir
   `aire_turn_id`. En `_resumer`, si la fila trae `aire_turn_id` → `reattach`
   en vez de `runner(req, resumed=True)`; sólo si el reattach dice "no existe"
   se re-pregunta. Quitar entonces la nota de reintento del camino reattach.

## The decision that's the owner's

Es trabajo cross-repo (aire-server + free-intelligence + aquí) con un release de
fi-runner en medio. Bernard decide cuándo entra; hasta entonces la fase A es
honesta por escrito: reanudar = re-preguntar.

## Status / next step

Not built. Recibo para arrancar: un restart del runner a media generación
(`az containerapp revision restart`) con `aire_route_turn_resumed` en KQL y UNA
sola respuesta en #general — ése es el estado actual; la fase B se mide por que
`aire_route_turn_resumed` deje de mandar un segundo mensaje al transcript de AIRE.
