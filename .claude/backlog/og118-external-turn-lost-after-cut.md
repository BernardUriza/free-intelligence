# OG118-EXTERNAL-TURN-1 — el turno externo se produce y se tira: el proxy corta, el motor termina solo, y Reintentar lo corre dos veces

Status: **In progress** — tres PRs el mismo día (presupuesto, entrega tardía, aviso en la UI); Done cuando haya recibo E2E en app.og118.ai (un turno de Yodo que pase la espera viva, muestre el aviso y aparezca en el hilo sin recargar)
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
- **Convergencia al contrato de eventos** (Art. 6): el externo sigue siendo single-shot. Que
  persona-runner emita el turno como stream (SSE) y og118 lo reenvíe como el path local mataría la
  espera viva como concepto. Es trabajo en server-bot, no en og118.
- **Idempotencia en el motor** (mismo `channel_id` + mismo `user_text` en N minutos = devolver el
  turno guardado) sigue siendo deseable para el *Reintentar* de un error real, pero dejó de ser
  urgente: el corte ya no produce error.

## La decisión que era de Bernard, y ya no hace falta

`persona-runner` con `minReplicas: 1` (2 vCPU / 4 Gi 24/7, del orden de cien dólares al mes) quitaba los
38 s de arranque. Con la entrega tardía el arranque en frío deja de perder respuestas; la réplica
caliente sólo compraría latencia, y eso se decide por costo cuando haya usuarios que la paguen.

## Status / next step

In progress. Siguiente paso: recibo E2E en app.og118.ai tras el deploy del segundo PR. Evidencia del
origen: logs de `persona-runner` y `og118-api` del 2026-10-15 19:42–19:46 UTC (`az containerapp logs show`).
