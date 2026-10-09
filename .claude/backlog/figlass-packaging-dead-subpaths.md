# FIGLASS-PACKAGING-1 — subpaths sin consumidor, el contrato de Tailwind sin declarar, tests que no fallan

Status: **Proposed**
Proposed: 2026-10-09 by Claude (hallazgos IMPORTANT del /cruel-critic, [[figlass-review-2026-10-09]])

## What it is

1. **`src/form`, `src/feedback` y `src/surface`** (~945 LOC, agregados el 30–31 de agosto) no tienen ningún consumidor: ni en el monorepo, ni en python-bot, ni en masterdomgdl. El "consulta-medica canary" que cita `surface` no existe.
2. **El contrato de Tailwind no está declarado**: fi-glass hornea utilidades en su dist y funciona solo porque og118 y Fénix agregan `../../packages/fi-glass/dist/**` a su `content`. Nada en `package.json` lo dice; un consumer externo de npm saldría sin estilos.
3. **`vitest`, `@testing-library/react` y `jsdom` no los declara fi-glass**; resuelven por el hoisting de otros workspaces. Es la ruleta que prohíbe `react-type-resolution.md`.
4. **Tests de layout por string** que no pueden fallar por la cascada: `ComposerFrame.test.tsx:148-157` (selector y `margin-right:auto` buscados en cualquier parte de la hoja), `WorkspaceDetailLayout.test.tsx:62-75` (`slice(indexOf)` corre hasta el final), `AgentConversationSurface.contained.test.tsx` ("scrolls internally" contra strings inline).
5. `splitting:false`: el bundle `agent` (151 KB) carga su propia copia de composer, messages, voice y shell, y `mqlCache` vive en 3 bundles.
6. npm tiene fi-glass 1.3.0 y main va en 1.7.0.

## Canonical path to reuse (Art. 6)

- #1: CLAUDE.md, NO LEGACY CODE. La evidencia de [[framework-first-canary]] § DEMOTION (cero consumidores, verificado con grep) aplica, pero aquí ni siquiera hay dueño al cual devolverlo: se borra.
- #2: un `README` de consumo y un campo en `package.json` (`"fiGlass": { "tailwindContent": "dist/**/*.{js,mjs}" }`), o un preset de Tailwind exportado que lo incluya.
- #3: devDeps explícitas en fi-glass.
- #4: reescribirlos para que fallen sin el fix (verificado contra main), o borrarlos y que lo cubra la medición en Chrome.

## The decision that's the owner's

**#1 es la que le toca a Bernard**: si `form`/`feedback`/`surface` eran trabajo para un producto que planea retomar, son backlog vivo; si no, se borran. La regla del CLAUDE.md dice borrar; la tarjeta no lo hace sin su sí, porque son 945 líneas de trabajo suyo.

## Status / next step

#2, #3 y #4 sin empezar y sin decisión pendiente. #1 espera a Bernard.
