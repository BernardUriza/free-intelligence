# FIGLASS-CASCADE-LAYOUT-1 — lo que jsdom no ve: cascada, breakpoint y primer paint

Status: **In progress** — #1, #2, #4, #5 y #6 Done 2026-10-09 (medidos en Chrome a 390×844 touch y en escritorio); queda #3 (breakpoint 768)
Proposed: 2026-10-09 by Claude (hallazgos IMPORTANT del /cruel-critic, [[figlass-review-2026-10-09]])

## What it is

La misma familia que el bug del padding: fi-glass da por hecha una cascada que el consumer no le da, y los tests de markup salen verdes.

1. **`glass-chat.css:147`** (`.glass-chat-composer [data-fi-composer-slot='area']`, especificidad 0,2,0) le gana al padding compacto de og118 `.og-composer-area` (0,1,0) dentro de `@container ≤420`. El comentario de la línea 145 dice lo contrario.
2. **`.fi-touch-target`** inyecta `align-items:center; justify-content:center; display:inline-flex` a `ResourceCard`/`DocCard`. En touch o ≤768 las tarjetas de Proyectos salen centradas, y `flex` contra `inline-flex` se decide por qué hoja se inyectó primero.
3. **Breakpoint 768 dividido**: fi usa `≤768px` y Tailwind `max-md:` usa `<768px`. Exactamente a 768 (iPad vertical) el shell entra a móvil y los mensajes siguen con el indent `pl-8` y texto de 14px de escritorio.
4. **Las 13 hojas `ensure*Style` se inyectan en `useEffect`**, después del primer paint, en un export estático. Las acciones se ven y luego colapsan, y en el drawer el contenido brinca unos 60px. Medir con un performance trace (layout shift) antes de arreglar.
5. El `:disabled` del Enviar tiene cursor `default` en vez de `not-allowed`: el preflight le gana a `:where()` (medido en prod).
6. El rail-toggle (`display:none`) y `.fi-touch-target` (`display:inline-flex`) empatan entre hojas distintas; el orden de inyección decide.

## Canonical path to reuse (Art. 6)

- La regla de #524: forma y garantías con especificidad de clase, color en `:where()`.
- #3: un solo breakpoint. `theme/breakpoints.ts` define el canon (≤768) y las variantes `max-md:` de fi-glass deben coincidir: un screen `md` propio en el preset, o mover esos estilos a la hoja inyectada.
- #4: `useInsertionEffect` (hecho para inyectar CSS) o una hoja estática exportada que el consumer importa.
- Verificación: el protocolo de `.claude/rules/mobile-viewport-ux.md` (harness efímero, 374px, `getBoundingClientRect`).

## The decision that's the owner's

#4 tiene una bifurcación real: `useInsertionEffect` (el contrato no cambia) contra CSS estático importado (requiere que cada consumer lo importe, pero mata el FOUC del todo). Recomendación: `useInsertionEffect` primero, medir, y escalar solo si el layout shift sigue.

## Status / next step

Hecho el 2026-10-09 (test `theme/cascadeContract.test.ts`, 6 de 6 rojos sobre main):
- **#1**: los slots del composer en `:where()`. En prod a 374px el área tenía `11.2px 13.6px 4px`; ahora el compacto de og118, `8px 8.8px 4.8px`.
- **#2**: el centrado de `.fi-touch-target` pasa a `:where()` (el mínimo de 44 sigue siendo garantía) y las tarjetas declaran `align-items: stretch`. Al medir apareció que **el módulo `resource` usaba la clase sin inyectar su hoja**: `ensureResourceStyle` ahora la garantiza. Con viewport touch: `stretch`/`flex-start`, `min-height: 44px`.
- **#5**: cursor `not-allowed` del Enviar deshabilitado, con especificidad de clase.
- **#6**: se resolvió con #2, porque el `display` del touch target ya no empata con el `display:none` del rail-toggle.
- **Hallazgo nuevo, también hecho**: en compacto el área no era el miembro flexible de la fila (el selector excluía `[data-fi-composer-slot]`) y sobraban 18px después de Enviar. Ahora el área llena la fila y el frame compacto lleva `padding: 0.25rem 0.3rem`: caja de 54px (tope 64), 6px a los lados, 5px arriba y abajo, overflow 0. Escritorio sin cambios.

- **#4, también 2026-10-09**: se midió antes de tocar código. Sin throttling, prod dio CLS 0.00. Con CPU ×4 y Slow 4G, **CLS 0.29**, y lo que se movía eran el mic, Enviar y el ícono del menú: elementos cuyas hojas llegaban por `useEffect` después del paint. El HTML estático (9 KB) no trae el shell; la UI aparece en un commit de React, así que `useInsertionEffect` sí llega antes de ese paint. Las 11 inyecciones se movieron ahí. Local, mismo origen y mismas condiciones: **CLS 0.40 (main) → 0.01 (fix)**. Candado: `theme/stylesBeforePaint.test.ts`, rojo sobre main con los 11 archivos.

Queda #3 (unificar el breakpoint 768).
