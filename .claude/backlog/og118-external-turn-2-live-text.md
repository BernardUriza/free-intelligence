# OG118-EXTERNAL-TURN-2 — el texto del elemento externo aparece mientras se escribe

Status: **Done 2026-10-15** — recibo E2E en app.og118.ai. La prueba del streaming es la serie de longitudes del DOM muestreada a 1 Hz (abajo); el screenshot `evidence/og118-external-turn-2-live-text-prod-2026-10-15.jpg` es el estado ASENTADO del cuarto turno (la captura llegó ~2 s tarde: cinco párrafos se escribieron en ~12 s), útil para ver que no quedó marcador ni duplicado. Con el runner en frío, la respuesta de Yodo creció en la burbuja viva de 0 a 2,643 caracteres en ~10 s (muestreo del DOM a 1 Hz: 201 → 488 → 805 → 1129 → 1336 → 1600 → 1895 → 2146 → 2251 → 2643), ningún `[REACT:`/`[GIF:` visible en ninguna muestra, y al asentar la primera oración aparece UNA vez (sin duplicado) con seis reacciones como chips. PRs #552 (AIRE), #553 (persona-runner), #554 (og118)
Proposed: 2026-10-15 by Bernard ("que venga directamente desde el LLM, que sirve AIRE"; autorizada la fase 2 completa el mismo día)

## What it is

Con OG118-EXTERNAL-TURN-1 los **verbos** (`tool_call`) de un elemento externo llegan en vivo por la
bitácora del boleto, pero el **texto** seguía siendo single-shot: AIRE emitía `text` una vez por
bloque completo (para una respuesta de un bloque, una vez al final), y persona-runner sólo reenviaba
`tool_call` porque el post-proceso de marcadores (`[REACT:]`, `[GIF:]`) opera sobre el texto final.

Fase 2 = el texto token a token, por el mismo camino, sin inventar un tercer mecanismo:

1. **AIRE** (`#552`): `include_partial_messages=True` en la costura de Claude; `engine/deltas.py`
   emite cada `text_delta` como `text` y, cuando llega el `TextBlock` completo (el SDK lo sigue
   mandando, antes de su `content_block_stop`), emite sólo la cola que los deltas no cubrieron —
   nunca el bloque dos veces. `text`/`answer` del resultado salen de los bloques completos, igual
   que antes. Los helpers de cobro se mudaron a `engine/billing.py` (el drainer estaba en el tope
   de 150 líneas).
2. **persona-runner**: el tap reenvía `text` a la bitácora tras `engine/live_text.MarkerFilter`
   (retención de sufijo: publica lo que ya no puede ser marcador, retiene lo que aún podría, descarta
   el marcador al cerrar, tope de 64 chars para uno abierto). El resultado conserva el F5 completo.
3. **og118**: `_tail_events` reenvía `text` además de `tool_call`; si streameó texto, al asentar
   sólo manda `result` (el reducer de core APPENDea `text` y REEMPLAZA en `result`: mandar el texto
   entero al final lo duplicaría).

Cero cambios en el contrato, core, fi-glass y og118 web: `text` ya era un delta por contrato.

## Canonical path to reuse (Art. 6)

- El algoritmo del filtro es el de `extractReasoningMiddleware` del AI SDK (histerical-search
  2026-10-15); no hay librería Python para esto, son ~60 líneas con su tabla de casos.
- El tap local (`turn_tap.py`) sigue siendo la deuda de que fi-runner llegue a persona-runner desde
  conda: cuando se publique fi-runner 0.24 con `on_event` en `AIREBackend.run_turn`, el tap se retira.

## The decision that's the owner's

Ninguna pendiente: Bernard eligió la fase 2 completa, incluido tocar AIRE (que también sirve a los
bots de Discord y a BAIR). Los consumidores que leen `text` lo tratan como delta (append) o lo
ignoran, verificado antes de prender los deltas.

## Status / next step

In progress. Siguiente paso: cuando los tres deploys estén vivos, E2E en app.og118.ai con el runner
frío: la respuesta de Yodo apareciendo por tokens, los `tool_call` intercalados, ningún marcador
visible, y el `result` sin duplicar el texto. Screenshot a `evidence/`.
