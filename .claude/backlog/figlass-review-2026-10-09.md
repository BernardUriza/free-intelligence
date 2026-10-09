# FIGLASS-REVIEW-2026-10-09 — /cruel-critic sobre fi-glass: los GRAVE que llegaron a producción

Status: **Done 2026-10-09** (residual: G1+G2 sin observar en vivo, ver abajo)
Proposed: 2026-10-09 by Claude (Bernard pidió "busca más defectos en fi-glass /cruel-critic" tras el bug del padding del composer)

## What it is

Arrancó con un bug que Bernard vio: el borde de **Llamar** pegado a su texto y **Enviar** en 18×18. La causa raíz: desde fi-glass 1.6.0 la FORMA de `ComposerActionSlot` iba en `:where()` (especificidad 0) y el preflight de Tailwind `button { padding: 0 }` le ganaba. Eso abrió una revisión en 4 dimensiones (cascada CSS, touch/a11y, estado/async, packaging). Los reportes completos están en `~/Desktop/fi-glass-review/`.

## Lo que se entregó (main, verificado en app.og118.ai)

| PR | Hallazgo | Recibo |
|---|---|---|
| #524 `a5c78d4` | La forma del composer sube a especificidad de clase; el color sigue en `:where()` | Prod: Llamar 85×31 con `padding 4.8px 10.4px`, Enviar 34×34; a 374px, Enviar 44×44 y overflow 0 |
| #525 `3dd106a` | **G3**: Enter en una acción del sidebar seleccionaba la fila · **G4**: `<ol>` pintaba • en vez de números · **G5**: `ChatFilePreview` usaba 11 clases que solo define aurity · **G6**: quitar-imagen medía 20×20 | 6 tests rojos sobre main, verdes con el fix; prod: el chat "razzia" ya numera |
| #526 `f976af6` | **G1**: el swap local→nube a media respuesta saltaba al chat más reciente y perdía la pregunta · **G2**: la migración no subía un turno local de un chat que ya existía en la nube. El turno ahora recuerda su `conversationId` | 9 tests rojos→verdes, más uno propio: la fusión con una copia vieja de la nube no corta el turno en vuelo |
| #527 `cd49430` | 6 usos de marca en `emerald` fijo pasan a `--fi-accent`; el verde semántico (éxito) se queda | Harness en Fénix: link `rgb(224,80,0)`; prod og118: `rgb(52,211,153)`, sin cambio |
| #523, #528 | Línea de versión en el sidebar; dato de que `fenix-web` no tiene workflow en el CLAUDE.md | — |

## Residual

- **G1+G2 no se han observado en vivo.** Requieren un cold start real de `og118-api` (minReplicas 0, ~21 s). Prueba: primer uso del día, mandar un mensaje en los primeros 20 s; debe quedarse en el chat donde se escribió.
- **Fénix sigue con el build de septiembre**: está pausado y su SWA no tiene workflow. Redesplegarlo es decisión de Bernard.
- Los hallazgos IMPORTANT/MINOR quedaron en cuatro tarjetas: [[figlass-state-residuals]], [[figlass-cascade-layout-residuals]], [[figlass-touch-a11y-residuals]], [[figlass-packaging-dead-subpaths]].
