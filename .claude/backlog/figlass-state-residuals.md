# FIGLASS-STATE-RESIDUALS-1 — lo que el turno-dueño-de-su-chat (#526) no cerró

Status: **Proposed**
Proposed: 2026-10-09 by Claude (hallazgos IMPORTANT/MINOR del /cruel-critic, [[figlass-review-2026-10-09]])

## What it is

Todo verificado leyendo el código, ninguno reproducido en navegador:

1. **Un append del servidor llega mientras hay un turno pendiente y el siguiente persist lo pisa.** Una recarga adopta el record nuevo sin hidratar; el siguiente poll no hace nada porque `updatedAt` ya coincide; el persist sube el hilo sin el mensaje del worker. Pega con OG118-BACKGROUND-1 (`origin: background`).
2. **Un timeout borra el texto del composer.** El gate de envío lee `conversation.isStreaming` y `send` lee `agent.isStreaming`. `onSend` limpia texto e imágenes, y luego `send` no hace nada. En og118 la ventana es de milisegundos; con un transport sin `abort` es permanente.
3. **`useDurableRecording`** (og118 lo usa): no limpia al desmontar, así que el mic queda vivo; un permiso concedido después del timeout de 15 s deja el stream sin dueño; un doble tap deja otro stream suelto.
4. **Object URLs sin revocar** en `useVoice.close` y en `AudioQueueItem`.
5. Una imagen que se sigue codificando al enviar se adjunta al mensaje **siguiente**.
6. Un Stop antes del primer token deja la pregunta en pantalla pero nunca la guarda.

## Canonical path to reuse (Art. 6)

- #1: la misma regla de #526, que el hilo en vuelo es la fuente. Si llega un `seedVersion` con un turno pendiente, fusiona por (role, timestamp, content) con `mergeConversationRecords` en vez de descartar.
- #2: un solo predicado de "puede enviar", el de `useAgentConversation`; el composer lo consume y no recalcula.
- #3–#4: las fugas se arreglan con `useEffect` de limpieza; `AudioDraftPlayer` ya revoca bien y sirve de patrón.

## The decision that's the owner's

Ninguna: son bugs. El orden lo marca el uso; #1 importa cuando el background execution se use de verdad.

## Status / next step

Sin empezar. Cada uno lleva su test rojo sobre main antes del fix, como en #525/#526.
