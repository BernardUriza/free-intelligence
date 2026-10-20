# FIGLASS-PACKAGING-1 — subpaths sin consumidor, el contrato de Tailwind sin declarar, tests que no fallan

Status: **In progress** — #1 Done 2026-10-09 (Bernard eligió borrar: `form`/`feedback`/`surface` fuera de src, dist, exports y tsup; 1,479 líneas; recuperables desde `ac499410`). #2–#5 Done 2026-10-19. Queda #6 (publicar en npm), que es decisión de Bernard
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

**#6 (2026-10-19)**: publicar es un acto hacia afuera y no se hizo. Estado medido: npm tiene `fi-glass` y `@free-intelligence/core` en 1.3.0 (18-jun); main va en fi-glass 1.9.0 y core 1.11.0. `publish-fi-ts.yml` exige que las DOS versiones coincidan con el tag `fi-ts-v*`, así que hoy ningún tag pasaría su guardia; además ambos paquetes ya son PolyForm Noncommercial, y el 1.3.0 publicado salió con otra licencia. Bernard decide: alinear versiones y cortar `fi-ts-v<x>`, o declarar npm abandonado (deprecar 1.3.0 y quitar el workflow).

**#1 era la que le tocaba a Bernard**: si `form`/`feedback`/`surface` eran trabajo para un producto que planea retomar, son backlog vivo; si no, se borran. La regla del CLAUDE.md dice borrar; la tarjeta no lo hace sin su sí, porque son 945 líneas de trabajo suyo.

## Status / next step

#1 hecho: grep previo sin consumidores (monorepo, python-bot, masterdomgdl, activist-os; el único import raíz era `ActionMenu` en aurity); después del borrado el grep de referencias vivas da cero, fi-glass 633/633, og118 128/128, og118-web y fenix-web compilan, y los 20 errores de `tsc` de aurity son los de dominio que ya existían (ninguno toca fi-glass). #2, #3 y #4 sin empezar y sin decisión pendiente.

### 2026-10-19 — #2, #3, #4 y #5

- **#2 contrato de Tailwind**: export `fi-glass/tailwind` (`tailwind.cjs`, en `files`) con los globs absolutos del dist. og118 y Fénix lo esparcen en `content` en vez de repetir `../../packages/fi-glass/dist/**`. Candados: `src/packageContract.test.ts` (export publicado; el glob cubre el dist que trae `messageStyles`) y `og118/web/app/__tests__/tailwindContract.test.ts`, que compila el config real de og118 con Tailwind y exige una utilidad que sólo fi-glass usa (rojo al quitar la línea del config). README actualizado.
- **#3 devDeps**: `vitest`, `jsdom`, `@testing-library/{react,dom,user-event,jest-dom}` declaradas. Candado: todo paquete importado desde `src` (tests incluidos) debe estar declarado. Sobre main: 151 imports sin declarar (vitest, RTL, user-event, jest-dom).
- **#4 tests que no podían fallar**: helper `src/test-utils/cssRules.ts` (parsea la hoja inyectada con el CSSOM, regla exacta bajo condición exacta). Prueba de mutantes: mover `margin-right:auto` de `footer-start` a `footer`, quitar `flex-direction:column`/`width:100%` del bloque móvil, y quitar el `minHeight:0`/`overflowY:auto` del transcript. **Los tres viejos siguen verdes con los mutantes (20/20)**; los nuevos se ponen rojos con cada uno (incluido el mutante que sólo quita `minHeight:0`) y verdes sin ellos. `contained` ahora renderiza en jsdom y recorre la cadena raíz→scroller.
- **#5 `splitting:true`**: JS del dist 731 KB → 349 KB; `mqlCache` vive en un chunk (antes en 3 bundles). Las entradas quedan como re-exports sin `'use client'`, y cada chunk con un módulo cliente lo abre con la directiva. Candados en `packageContract.test.ts`: un solo `mqlCache` (rojo con `splitting:false`: 3 archivos) y "todo archivo del dist que trae un módulo `'use client'` abre con la directiva" (rojo al borrarla de un chunk).
- Consumidores: og118-web tsc + vitest 129/129 + `next build`, fenix-web `next build`, aurity `next build`; los 20 errores de `tsc` de aurity son los mismos 20 antes y después (diff vacío por archivo). El CSS servido de og118 y Fénix trae las utilidades de fi-glass.

