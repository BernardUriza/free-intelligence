# B3-FIGLASS-RESOURCE-ADOPTION-1 — la página de Proyectos todavía es CSS de og118, no anatomía de fi-glass

Status: **En curso** — primer corte entregado 2026-09-10: `globals.css` **771 → 664** medido
Proposed: 2026-09-09 by Claude — es la tarjeta que [[b3-figlass-shell-primitives]] prometía al cerrar 1D y que nunca existió

## Qué es

`B3-FIGLASS-SHELL-PRIMITIVES-1` cerró el arco del **shell** (sidebar, composer,
resource rail) y dijo, textual, que lo que quedaba de `globals.css` *"no es
anatomía del shell: es la página de Proyectos, que es su propia tarjeta"*. Esa
tarjeta no se escribió. Ésta es.

**El hallazgo que la cambia de forma: no es una extracción, es una adopción a
medias.** `fi-glass/resource` YA existe y ya está exportado
(`fi-glass/src/index.ts:37`) con nueve componentes, todos con test:
`ResourceIndexHeader`, `ResourceCardGrid`, `ResourceSearchInput`, `DocCard`,
`RailPanel`, `CapacityMeter`, `WorkspaceBreadcrumb`, `WorkspaceDetailLayout`,
`resourceStyle`. Y og118 ya lo consume en dos archivos —
`Og118ProjectsIndex.tsx` y `Og118ProjectWorkspace.tsx`.

Y aun así **273 de las 771 líneas de `apps/og118/web/app/globals.css` siguen
siendo `og-project*`** (43 bloques, 26 selectores únicos, medido). La adopción se
quedó en el esqueleto: el marco lo pinta fi-glass, el CONTENIDO del detalle sigue
siendo CSS local.

## Dónde está concentrado (medido, no estimado)

| Archivo | Clases `og-project*` |
|---|---|
| `Og118ProjectWorkspace.tsx` | **15** — heading + acciones de rename inline, form y preview de `instructions`, lista de recientes, error, cta |
| `Og118ProjectsSection.tsx` | 5 — la sección del sidebar (empty, list, new, nav) |
| `Og118ProjectsIndex.tsx` | 5 — page, cta, sort, sort-label, note |
| `Og118ProjectUploadPanel.tsx` | 3 — botón y estado de subida |
| `Og118ProjectsPage.tsx` / `app/projects/page.tsx` | 3 c/u — shell, nav, note, edit |
| `Og118ProjectCreateRow.tsx` | 1 |

El 58% del residuo vive en `Og118ProjectWorkspace.tsx`. **Ése es el corte.**

## Camino canónico a reusar (Art. 6)

`fi-glass/resource` es el destino y ya existe — esto NO abre un módulo nuevo. La
pregunta de diseño de cada clase es la misma que ganó en 1D: *¿esto es anatomía
(la forma que cualquier workspace de recursos tiene) o es marca de og118?*

- **Anatomía → sube**: el encabezado de un detalle con su acción de rename
  inline; el bloque de "instrucciones" (form ↔ preview) que cualquier workspace
  con reglas propias necesita; la lista de "recientes" con su timestamp.
- **Marca → se queda**: colores, degradados, tipografía, copy.
- **La lección de especificidad de 1D aplica entera**: los DEFAULTS del framework
  van en `:where()` (especificidad 0), las GARANTÍAS no. Es lo que evitó que el
  primitivo borrara el degradado esmeralda del botón de enviar.

## Criterios de aceptación

- `Og118ProjectWorkspace.tsx` deja de nombrar clases de layout propias; su
  estructura la pinta `fi-glass/resource`.
- `globals.css` baja de 771; el número final se REPORTA medido, no prometido.
- Cada primitivo nuevo llega con test en fi-glass, como los nueve que ya están.
- **Medición obligatoria a 374px en Chrome real** antes de aprobar
  ([[mobile-viewport-ux]] § protocolo) — la página de Proyectos nunca se ha
  medido a ancho de teléfono, y un test SSR que encuentra el markup no prueba
  layout.
- Nada de slots especulativos: si og118 no lo consume, no se construye
  ([[framework-first-canary]] — 1D ya rechazó un `footerEnd` por esa razón).

## La decisión que es del dueño

Si el arco vale la pena AHORA. Argumento a favor: es el último bloque grande de
`globals.css` y el único consumer de `fi-glass/resource` es og118, así que el
primitivo está sin ejercer de verdad. Argumento en contra: la página funciona, y
[[figlass-projects-page]] dejó su propia Fase 2 pendiente (composer en la
página, pin/archive de proyectos) — que es FUNCIÓN, no forma. **Si sólo hay
presupuesto para uno, la función le gana a la anatomía.**

## Estado / siguiente paso

Sin empezar. El primer corte natural es `Og118ProjectWorkspace.tsx`, que es donde
está el 58% del residuo.

Ver [[b3-figlass-shell-primitives]] (el arco hermano, cerrado; esta tarjeta es la
que prometió), [[figlass-projects-page]] (la FUNCIÓN de la misma página, con su
Fase 2 abierta), [[framework-first-canary]] y [[mobile-viewport-ux]].

## Corte 1 — `Og118ProjectWorkspace.tsx`, 2026-09-10

**Dos primitivos nuevos en `fi-glass/resource`**, los dos por evidencia y no por
diseño especulativo:

- **`EditableSection`** — og118 escribía la misma forma de vista⇄edición DOS
  VECES en el mismo archivo. Sube el MARCO (el `<form>`, la fila de acciones, la
  línea de error), no la máquina: cuál campo, guardado async y validación son
  producto. `useInlineRename` de `fi-glass/agent` se dejó en paz — es de un solo
  valor con commit al blur y no encajaba; construir una segunda máquina habría
  sido el olor.
- **`ResourceListSection` / `Items` / `Row`** — cabecera con acción y filas de
  (título, meta). Estado vacío y de carga quedan como `children` del consumidor:
  un componente con su propio *"no hay nada todavía"* ya eligió un idioma.

**Resultado medido:** de 15 clases `og-project*` en ese archivo a **5**, y las 5
que quedan son marca real (`cta`, `edit`, `note`, `page`, `heading`). 18 bloques
de CSS quedaron sin un solo consumidor —verificado por grep— y se borraron.

### Lo que la medición obligatoria destapó, y es lo más valioso del corte

1. **El bloque táctil prometía lo que no hacía.** Su comentario cita los números
   exactos (*"el CTA quedaba en 37px, Editar en 34 y el select en 30 — todos por
   debajo del mínimo de 44"*) y la regla dentro era **sólo `flex-wrap: wrap`**.
   Nunca hubo `min-height`. Mi medición independiente dio esos MISMOS números, lo
   que prueba que el arreglo se escribió, se documentó y no se aplicó. Ahora el
   `min-height: 44px` existe y el `wrap` se movió al contenedor.
2. **Selectores muertos:** `.og-projects-heading--editing input/textarea` seguían
   citados en dos bloques después de que la clase dejó de existir.
3. **fi-glass no tenía auto-cleanup de Testing Library.** Sin `globals: true` ni
   un `afterEach` registrado, cada `render` se quedaba pegado en el `body` y el
   caso siguiente lo veía; un `screen.*` global podía leer el DOM del test
   ANTERIOR. Lo descubrió un rojo mío. Registrado: 627 verdes, ninguno dependía
   de la fuga.

**Recibos:** contenedor de 374px en Chrome real, media táctil activa, overflow 0
en documento/arnés/head/detalle/rail, los cuatro botones a **44px** (antes
44/34/37/34), screenshot tomado y arnés efímero borrado sin commitear. fi-glass
**627** verdes (9 nuevos), og118-web **116**, cero errores de tipos.

### Lo que sigue

`Og118ProjectsSection` (5 clases), `Og118ProjectsIndex` (5), `Og118ProjectUploadPanel`
(3) y las de página. Ninguna concentra como concentraba el detalle, así que el
resto es un arco más plano.
