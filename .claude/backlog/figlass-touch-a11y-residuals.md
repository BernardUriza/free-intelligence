# FIGLASS-TOUCH-A11Y-1 — targets menores a 44 y el foco del drawer

Status: **Proposed**
Proposed: 2026-10-09 by Claude (hallazgos IMPORTANT del /cruel-critic, [[figlass-review-2026-10-09]])

## What it is

Contra `.claude/rules/mobile-viewport-ux.md` (touch ≥44×44 siempre). Tamaños estimados desde el CSS; cada uno se mide antes de arreglar:

1. **Menos de 44 y llegan a og118**: Retry/Dismiss de `TurnErrorBanner` (~28), "Ver más" de `CollapsibleText` (~18, en cada mensaje largo), el trigger de elemento/persona (~38), los items de `ActionMenu` (~34), `ResourceListRow` (~36).
2. **El rail-toggle mide 18×18** con un composer angosto en pantalla ancha. Recibe 44 solo por viewport; `composerActionStyle.ts` ya resolvió esto mismo para Enviar.
3. **Acciones invisibles de 44px se comen el título del sidebar** en una ventana angosta con mouse: el mínimo de 44 aplica con touch O con ≤768, pero el reveal solo con touch.
4. **Drawer**: no mueve el foco al abrir, el toggle se desmonta y el foco cae al body; no tiene `role="dialog"`/`aria-modal`; `aria-expanded` siempre es false; le falta el safe-area de abajo y de la izquierda (og118 lo parcha en su CSS, el siguiente consumer no).
5. **Acciones por mensaje en touch con teclado o lector de pantalla** (iPad con teclado, VoiceOver): fuera del último mensaje están ocultas, y el `<article>` que se revela con un tap no tiene rol.
6. Los popovers (`ActionMenu`, `PersonaSelector`) no se ajustan al viewport: la lista de 360px se desborda en 320px.

## Canonical path to reuse (Art. 6)

`withTouchTarget` + `useTouchTargetStyle` en el componente que usa la clase (hoy varios dependen de que otro componente ya la haya inyectado). Para #2, la regla `@container fi-composer` de `composerActionStyle.ts`.

## The decision that's the owner's

Ninguna: la regla de móvil ya está decidida.

## Status / next step

Sin empezar. Primero medir todo con el harness a 374px; arreglar en un solo PR por componente.
