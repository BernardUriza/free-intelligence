# FIGLASS-TOUCH-A11Y-1 — targets menores a 44 y el foco del drawer

Status: **Done 2026-10-19**
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

**Done 2026-10-19.** Every item got a test that failed on `origin/main` (17/17 red, run against main's `src/` in a detached worktree) and passes after the fix: `apps/packages/fi-glass/src/touchA11y.residuals.test.tsx`. jsdom does not lay out, so the sizes were measured in real Chrome (chrome-devtools MCP) on an ephemeral og118 route that rendered the REAL components, deleted before commit. Phone = 390×844 emulated touch, column 374px; narrow = 320 viewport / 304px column.

| # | Fix | Test (red on main → green) | Measured before → after |
|---|-----|---------------------------|-------------------------|
| 1 | `withTouchTarget` + `useTouchTargetStyle` in `TurnErrorBanner` (also when the consumer dresses the buttons), `CollapsibleText`, `PersonaSelector` trigger, `ActionMenu` items (default items keep `justify-content: flex-start`), `ResourceListRow`; `ItemActionSlot` and `composerActionStyle` now inject the touch sheet themselves instead of relying on a sibling | `item 1 — …` (7 tests) | Retry/Descartar 32.4 → **44**; "Mostrar más" 19.2 → **44**; element trigger 38 → **44**; menu items 37 → **44**; `ResourceListRow` 40 → **44**; every button inside the 374 column, 0px overflow |
| 2 | `ComposerFrame`'s `@container fi-composer (max-width: 420px)` gives `.fi-composer-rail-toggle` the 44 minimum; the frame ensures the touch sheet | `item 2 — …` | Wide window (no touch), composer at 374 and 304: toggle 18×18 → **44×44**, send inside the column, row overflow 0 |
| 3 | Sidebar item reveal + wrap moved from `(pointer: coarse)` to `FI_TOUCH_QUERY`, the same gate as the 44 minimum | `item 3 — …` | 700px window with mouse: two invisible 44px actions left the title 158px of a 280px row → actions visible, title **259px** |
| 4 | Drawer panel is `role="dialog"` + `aria-modal` (the `<nav>` landmark stays inside, `display: contents`); the dialog takes focus on open (never a search input that would raise the keyboard); the toggle stays mounted with a truthful `aria-expanded` + `aria-controls` and gets focus back on Escape / overlay / `api.close()`; the page behind is `inert`; the panel owns `env(safe-area-inset-bottom/left)` and og118's `.og-sidebar-foot` patch is deleted | `item 4 — …` (5 tests) | Before: focus on `<body>` after open and after close, toggle unmounted, no dialog role, padding 0. After: focus `div[role=dialog]` on open → `.fi-aws-toggle` on close, `aria-expanded` true/false, page inert, inline `padding-bottom/left: env(...)` |
| 5 | On coarse pointers the per-message actions are visually hidden (`clip-path: inset(50%)`), not `display: none`, and `:focus-within` reveals them | `item 5 — …` | Before: non-last message's copy button unfocusable (0×0). After: focusable, 1×1 clipped at rest, **44×44** visible on focus |
| 6 | `ActionMenu` and `PersonaSelector` cap their panel at `calc(100vw - 16px)` and clamp it horizontally inside an 8px margin | `item 6 — …` (2 tests) | 320 viewport: element list 360px wide (right edge 360) → 304 (8–312); menu from a trigger at x=200 ended at 408 → 104–312 |

Evidence: `evidence/figlass-touch-a11y-1-before-390-2026-10-19.jpg`, `…-after-390-…`, `…-after-menu-320-…`, `…-before-drawer-390-…`, `…-after-drawer-390-…` (the drawer change is behavioral; both drawer shots look alike).

Seen in the harness and left alone: `MessageBubble`'s own classes overflow a bare 374px column by 14px (the transcript gutters absorb it in og118).
