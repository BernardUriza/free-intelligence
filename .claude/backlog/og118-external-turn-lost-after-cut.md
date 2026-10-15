# OG118-EXTERNAL-TURN-1 — el turno externo se produce y se tira: el proxy corta, el motor termina solo, y Reintentar lo corre dos veces

Status: **Done 2026-10-15** — recibo E2E en app.og118.ai: `evidence/og118-external-turn-1-live-verbs-prod-2026-10-15.jpg` (Yodo, "1 step · WebSearch" pintado en vivo como ACTIVE a los 18 s y persistido como DONE sobre la respuesta). Seis PRs en el día: #545, #546, #547, #548, #549, #550
Proposed: 2026-10-15 by Claude (dogfood: Bernard reportó "está tardando mucho" en `og118.ai/c/d2742db6…`)

## Qué pasó (recibo, UTC 2026-10-15)

| Hora | Quién | Evento |
|------|-------|--------|
| 19:42:54 | og118-api | arranca en frío (minReplicas 0) |
| 19:43:06 | og118-api | `POST /chat/stream` del mensaje de Göbekli Tepe (elemento Yodo = `external_http_engine`) |
| 19:43:32 | persona-runner | arranca en frío (minReplicas 0, 26 s después del POST) |
| 19:43:40 → 19:43:51 | persona-runner | pipeline warm + prewarm de embeddings (20 s) y abre el topic en AIRE |
| 19:44:41 | og118-api | el proxy corta a los 95 s (`ReadTimeout`); el cliente guarda la conversación con el error |
| 19:45:11 | persona-runner | `turn_pipeline_completed`, 1135 chars + 6 reacciones — **nadie la escuchó** |
| 19:46:06 | persona-runner | extrae 3 facts a la memoria del usuario a partir de ese turno |

La respuesta existía en el motor (se guardó por el pipeline `runner`), og118 ya la había descartado,
y un *Reintentar* corría el MISMO texto otra vez: doble gasto, doble escritura de memoria, y el hilo
del motor con dos turnos del usuario iguales.

## Lo que se hizo (2026-10-15)

1. **PR #545 — la espera viva cuenta el arranque en frío.** De 95 s a 150 s: el techo del motor (90 s)
   **más** el arranque que corre ANTES de que el reloj del motor empiece. El comentario anterior
   ("95 > 90, así siempre corta el motor") comparaba dos relojes que no arrancan juntos.
2. **Segundo PR — pasada la espera viva, la respuesta no se tira.** `stream_external_turn` corre el
   `POST /v1/turn` como task; a los 150 s suelta al cliente con un turno vacío (fi-glass no dobla
   burbuja cuando no hay texto ni reacciones) y el task sigue. Al terminar, `deliver_late` escribe en
   el record el par mensaje-del-usuario → respuesta con `origin: background`, por
   `ConversationStore.append_late_turn` — el mismo camino que el worker de OG118-BACKGROUND-1, y la
   misma protección (`_keep_background_messages`) contra el `PUT` viejo del cliente. El sync de 15 s
   del cliente (`useOg118ConversationSync`) recarga el record y pinta el par. Si la conversación nunca
   se persistió (primer turno), el record se crea alrededor del par en vez de perderlo. Si el motor
   falla tarde, aterriza una nota visible con la razón, no el silencio. Sin hilo donde entregar
   (bearer legacy, sin conversation id) el corte sigue siendo un `error`.

   Ya no hay *Reintentar* que correr dos veces en el caso del corte: el usuario no ve error.

## Qué queda

- **Recibo E2E en producción** (cierra la tarjeta): un turno de Yodo que pase los 150 s y aparezca en
  el hilo por el sync. Reproducible dejando dormir `persona-runner` (cooldown 300 s) y mandando un
  mensaje largo.
- ~~**Señal en la UI mientras llega.**~~ Hecho el mismo día (tercer PR): el contrato gana el frame
  `deferred` (`fi_runner/events.py` → schema → TS → Swift), core lo reduce a `turn.deferred` y la
  conversación levanta un `notice` ("Yodo sigue escribiendo. Su respuesta aparecerá aquí en cuanto
  termine."); fi-glass lo pinta como `role="status"` con el mismo banner de fallo en tono info y sin
  Reintentar; se limpia al recargar el hilo, al mandar otro mensaje o al descartarlo. og118 web sólo
  mapea el frame. core 1.6.0, fi-glass 1.8.0.
- ~~**Convergencia al contrato de eventos**~~ Hecho (PR #548 server-bot + el PR de og118 del
  mismo día, plan `sparkling-waddling-feigenbaum`): og118 deja el `/v1/turn` síncrono (legacy según
  `robustness.md`) y monta el turno en el **boleto**: `POST /v1/turn/jobs` + `GET …/jobs/{id}/events`
  (SSE con cada `tool_call` real de AIRE, `id` secuencial, reanudable) + poll `GET …/jobs/{id}?wait_s=50`.
  Los verbos se pintan en el `StepsPanel` de fi-glass sin tocar core, fi-glass ni og118 web. El texto
  sigue llegando completo en `result` (los marcadores de la persona se recortan sobre el texto final).
- ~~**Idempotencia en el motor**~~ Hecha por construcción: el `job_id` se deriva de (conversación,
  posición en el hilo, texto), así que el reintento del cliente cae en `ticket_reused` y el turno no
  corre dos veces.
- **OG118-EXTERNAL-TURN-2 — texto en vivo** (fase 2, tarjeta propia): `include_partial_messages` en
  AIRE para deltas de texto, filtro de retención de sufijo en persona-runner para los marcadores
  (`[REACT:]`, GIFs) y `on_event` upstream en fi-runner 0.24 para retirar el tap local.

## La decisión que era de Bernard, y ya no hace falta

`persona-runner` con `minReplicas: 1` (2 vCPU / 4 Gi 24/7, del orden de cien dólares al mes) quitaba los
38 s de arranque. Con la entrega tardía el arranque en frío deja de perder respuestas; la réplica
caliente sólo compraría latencia, y eso se decide por costo cuando haya usuarios que la paguen.

## Recibo E2E (2026-10-15, UTC)

| Hora | Qué se observó |
|------|----------------|
| 23:16:11 | primer turno de prueba en una conversación nueva con Yodo (`a84c0bf0…`), runner en frío |
| 23:16:45 | `ticket_submitted` con el `job_id` derivado por og118; `POST /v1/turn/jobs` 202; `GET …/events` abierto un segundo después |
| 23:17:35 | respuesta con 6 reacciones en ~84 s (26 s de arranque incluidos); el runner llamó `ToolSearch` y `WebSearch`… **pero el panel no los pintó**: la bitácora nacía en `turn_via_aire`, ~10 s después del alta con `pipeline: runner`, y el tail recibió `done` → #550 |
| 23:35:02 | segundo turno tras desplegar #550 (`persona-runner--0000283`) |
| 23:35:22 | **"1 step · WebSearch · ACTIVE"** en pantalla mientras el turno corría (texto del DOM capturado a los 18 s) |
| 23:35:34 | `agent_runner_turn_complete`; poll 200; la respuesta cita Archaeology Magazine; el panel persiste "1 step · WebSearch · DONE" sobre la burbuja (screenshot) |

Lo que este recibo NO prueba, dicho con todas sus letras:
- **`ticket_reused` en vivo.** El `job_id` incluye la posición en el hilo, así que sólo colisiona el *reintento* del mismo envío (fi-glass tras un error, con el mensaje optimista revertido), no un segundo envío manual del mismo texto. Está cubierto por tests unitarios (`test_the_job_id_is_the_turn_not_the_attempt`, `test_the_same_job_id_posted_twice_runs_one_turn`); no se forzó un error real en producción para verlo.
- **La ruta diferida (>150 s) en producción.** Sigue cubierta por tests; hoy ningún turno real pasó de 84 s.

Observación colateral, fuera de alcance: durante el primer turno de una conversación **nueva** el cliente pidió `GET /conversations/{id}` unas 30 veces en 85 s y recibió 404 en todas (el record no existe hasta que el turno se asienta). Es ruido y costo de un poll sobre un id que aún no se persistió; va a `FIGLASS-STATE-RESIDUALS-1`.

Evidencia del origen: logs de `persona-runner` y `og118-api` del 2026-10-15 19:42–19:46 UTC (`az containerapp logs show`).
