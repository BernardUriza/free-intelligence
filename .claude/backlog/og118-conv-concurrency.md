# CONV-CONCURRENCY-1 — pin/título pierden en last-write-wins entre dispositivos

Status: Proposed
Proposed: 2026-07-13 by Claude (hallazgo del /cruel-critic sobre CONV-ORGANIZE-1, aceptado por Bernard)

## What it is

Toda mutación de conversación viaja como **put del record completo** (`PUT
/conversations/{id}`, patrón de CONV-CLOUD-1): rename, pin, archive y el
persist de cada turno reconstruyen y suben el JSON entero. Con dos
dispositivos activos sobre la misma cuenta, el último put gana el record
completo:

- Teléfono fija (`pinnedAt`) una conversación → desktop, con lista stale en
  memoria, manda un mensaje → su `persist` sube el record SIN `pinnedAt` → el
  pin se pierde en silencio. Lo mismo aplica a `titleCustom`/`title` (deuda que
  existe desde CONV-CLOUD-1) y a `archivedAt` (superficie ampliada por
  CONV-ORGANIZE-1, PR #362).
- No hay corrupción ni pérdida de mensajes (el persist siempre lleva el thread
  completo del dispositivo activo); se pierden los FLAGS de organización.

Mitigante actual: el cliente refresca la lista del server tras cada acción, así
que la ventana es "acción en A mientras B tiene estado viejo y persiste
después" — real pero angosta para un usuario single-owner (og118 es de uso
personal hoy).

## Canonical path to reuse (Art. 6)

Dos rutas, de menor a mayor cirugía — decidir cuando el multi-dispositivo sea
uso real y no teórico:

1. **Guard optimista barato**: el server rechaza (409) un put cuyo `updatedAt`
   sea ANTERIOR al almacenado; el cliente re-lee, re-aplica su delta puro
   (transformers de core: `setConversationPinned`/`renameConversationRecord`)
   y reintenta. Sin endpoint nuevo; ~20 líneas server + retry en
   `transformConversation`/`persist` de fi-glass.
2. **PATCH parcial de metadata**: endpoint `PATCH /conversations/{id}` que
   acepta solo `{title?, titleCustom?, pinnedAt?, archivedAt?}` y hace merge
   server-side; el persist de mensajes deja de tocar flags. Más limpio, más
   cirugía (nuevo verbo en store/app/librerías/tests).

## The decision that's the owner's

Si esta deuda amerita fix antes del multi-usuario/multi-device real, y cuál
ruta (guard 409 vs PATCH). Hoy no bloquea: og118 es single-owner y la ventana
de carrera es angosta.

## Status / next step

No construido. Se activa cuando Bernard reporte el primer pin/rename perdido
entre su Mac y su teléfono, o antes de abrir og118 a más cuentas. Referencias:
`useConversationLibrary.persist` (acarreo de flags), `conversations.py::put`,
PR #362/#364.
