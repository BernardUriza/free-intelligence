# FIGLASS-STATE-RESIDUALS-1 — lo que el turno-dueño-de-su-chat (#526) no cerró

Status: **In progress** — #1–#6 hechos con test rojo→verde (2026-10-19, rama `bernarduriza/figlass-state-residuals`); queda abierto el poll de 404 de #5
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
- #5 (2026-10-15, visto en el E2E de OG118-EXTERNAL-TURN-1): en una conversación **nueva**, durante el
  primer turno el cliente pide `GET /conversations/{id}` unas 30 veces en 85 s y recibe 404 en todas,
  porque el record no existe hasta que el turno se asienta. Es un poll sobre un id que aún no se
  persistió: o no se pollea mientras no haya record, o el 404 se recuerda hasta el primer persist.

## The decision that's the owner's

Ninguna: son bugs. El orden lo marca el uso; #1 importa cuando el background execution se use de verdad.

## Status / next step

Hecho 2026-10-19. Cada test se vio **rojo** sobre `e5597abe` antes del fix y verde después.
Nada de esto se ha observado en vivo en app.og118.ai: son pruebas unitarias/jsdom y el arnés de iOS.

| # | Dónde se arregló | Test (rojo → verde) |
|---|---|---|
| 1 | fi-glass `useAgentConversation`: un `seedVersion` con turno pendiente se fusiona al hilo vivo (`mergeConversationMessages`, nuevo, reusado por `mergeConversationRecords`) | `useAgentConversation.seedVersion.test.tsx` › *a server append that lands mid-turn survives the fold and is saved with it*; *merges the re-seed while a turn is streaming…* (antes afirmaba el descarte) |
| 2 | fi-glass: `AgentConversation.canSend` (el predicado de `send`) y `send` devuelve si salió; el surface gatea con él y limpia sólo si salió | `AgentConversationSurface.sendGate.test.tsx` › *a timeout on a busy transport never wipes the next draft*; *canSend follows the transport, and send reports whether it went out* |
| 3 | fi-glass `useDurableRecording`: un start a la vez, un `getUserMedia` tardío (tras el timeout de 15 s o el unmount) se detiene, unmount apaga mic/timer/recorder | `useDurableRecording.test.ts` › *unmounting while recording stops the mic*; *a permission granted after the 15s timeout does not leave an ownerless stream*; *a double tap on the mic never leaves a second stream running* |
| 4 | fi-glass `useVoice` (close y unmount revocan) y `AudioQueueItem` (libera audio + URL al desmontar, reanuda el mismo clip tras pausa) | `useVoice.test.tsx` › *close() revokes the clip it was showing*; *unmounting revokes the clip still open*; `AudioQueueItem.test.tsx` › *unmounting mid-play stops the audio and revokes its URL*; *pause then play resumes the same clip…* |
| 5 | fi-glass `useComposerImages.encoding` + generación que `clear()`/`restore()` invalidan; el surface retiene el envío hasta que la imagen está lista y la manda con ESTE mensaje | `useComposerImages.test.tsx` › *reports encoding while…*; *an encode that finishes after clear() never lands on the next message*; `AgentConversationSurface.sendGate.test.tsx` › *holds the send until the picked image is ready…* |
| 6 | **core** `conversation-state.ts` (`turn_settled` con `stopped` devuelve hilo nuevo con `skipPersist:false`) + iOS `ChatModel.cancel()` (tenía el mismo bug) | vector *parar el turno es una decisión…* ahora declara `saved` (campo opcional por vector; quien lo declara obliga a TS y a iOS a medirlo): rojo en `conversation-state-vectors.test.ts` y en el arnés iOS (`1 FALLARON`); hook: `useAgentConversation.test.tsx` › *saves the question when stopped before the first token* (rojo contra el dist viejo de core). El test iOS de cancelar ahora exige guardar la pregunta sola, sin la respuesta a medias |

**Abierto — el poll de 404 de #5 (no se tocó, a propósito).** No encontré en el código del web al
llamador con cadencia de ~3 s: los únicos `GET /conversations/{id}` del cliente salen de
`RemoteConversationLibrary.get`, y sus llamadores (`useConversationLibrary`: carga, switch,
`reloadActive`, persist de otra conversación, metadata) no pollean a 3 s; el único poll,
`useOg118ConversationSync`, va cada 15 s y se salta mientras hay streaming. Y el arreglo que
propone la tarjeta ("no pollear sin record") **rompería la entrega tardía** de un primer turno
diferido: `ConversationStore.append_late_turn` (apps/og118/server/conversations.py:203) crea el
record alrededor del par cuando no existe, y el cliente sólo lo ve si sigue pidiendo ese id.
Siguiente paso: captura de red real (DevTools) en app.og118.ai durante el primer turno de una
conversación nueva para nombrar al llamador; si es el web, el arreglo es dejar de pedir mientras
el turno está vivo, no mientras no haya record.
