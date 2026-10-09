# FIGLASS-CASCADE-LAYOUT-1 — lo que jsdom no ve: cascada, breakpoint y primer paint

Status: **Proposed**
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

Sin empezar. #1, #2 y #5 son de menos de una hora cada uno, con test y medición.
