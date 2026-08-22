# FIGLASS-PROJECTS-PAGE-1 — Projects como PÁGINA (paridad claude.ai), primitivas en fi-glass

Status: **Done** (fase 1 + instructions cableadas) — 2026-08-22; queda el composer en la página y pin/archive
Proposed: 2026-07-14 by Bernard ("quiero que sea una página, muy parecido a como
sucede en claude.ai, que se ven recuadros con contenido y todo ese spa")

## What it is

La sección Projects de og118 deja de ser una lista en el sidebar y se convierte
en una **página completa** con navegación SPA, calcando la anatomía de claude.ai
Projects: un **índice** (grid de cards) y un **detalle** (workspace de dos
columnas con composer + conversaciones + rail de knowledge). Las primitivas
suben a fi-glass como patrón genérico de "resource workspace" (fi-glass NO
conoce la palabra "project" — og118 la mapea), per [[framework-first-canary]].

## Specs medidos en la superficie REAL (claude.ai live, Chrome DevTools, 2026-07-14)

### A. Página índice (`/projects`)

Contenedor: `max-w-4xl` (896px) centrado, `px-4 md:px-8`.

1. **Header de página**: título "Projects" serif 24px/500 a la izquierda;
   a la derecha `Sort by <criterio>` (dropdown: Last updated) + CTA primario
   "New project" (pill, fondo claro invertido, radius 8px, 14px/500).
2. **Búsqueda full-width**: input "Search projects..." 40px de alto,
   radius 10px, fondo `rgba(255,255,255,0.1)`, filtra el grid en vivo.
3. **Grid de cards**: `<ul>` semántico — `grid-cols-1 gap-3` móvil,
   `md:grid-cols-2 md:gap-6` desktop (cards de ~404px en el 896),
   `auto-rows-fr` (filas de altura pareja).
4. **Card** (`<li>` > wrapper > `<a href=/project/{id}>`): flex-col,
   `gap 16px`, `padding 16px`, `radius 12px`, bg surface-1 (#1a1a19),
   hover → surface-2, `active:scale-0.98` con transición corta; ring shadow
   sutil (1px inner). Contenido: **título** 14px/600 blanco · **descripción**
   14px/400 muted (#c3c2b7) con `line-clamp: 3` · **"Updated <time>"** 13px
   muted (#898781, relativo: "6 days ago").
5. **Empty state**: cuando no hay proyectos, copy + CTA de crear (patrón ya
   existente en og118 sidebar — se reusa el copy).

### B. Página detalle (`/project/{id}`)

1. **Breadcrumb** arriba: `Projects / <nombre>` (link de regreso al índice).
2. **Header**: título serif 24px/500 + descripción debajo (14px muted).
   Acciones a la derecha: **Pin project** (icono) + **kebab "More options"**
   (rename / delete; claude.ai también archive/unarchive y star).
3. **Layout dos columnas** (desktop): columna principal ~577px + rail derecho
   **352px**; en móvil el rail se apila (colapsa bajo el main, PROBABLE —
   inferido de las clases responsive, no medido en 390px).
4. **Columna principal**:
   - **Composer arriba de todo** — el proyecto ES un punto de entrada de chat:
     escribir ahí crea una conversación nueva YA scoped al proyecto (corpus
     activo). Mismo ComposerFrame de fi-glass, reusado tal cual.
   - **"Recents"**: lista de las conversaciones del proyecto — filas de 36px
     (`min-h-9`), icono + título + tiempo relativo a la derecha, separador
     1px, click navega al chat.
5. **Rail derecho** (borde 0.5px, `radius 16px`, secciones apiladas separadas
   por divisores 1px de `rgba(226,225,218,0.15)`):
   - **Instructions** (~92px): preview truncado + lápiz para editar.
   - **Memory** (~112px): preview + badge "Only you" (og118: N/A fase 1).
   - **Context/Knowledge** (~245px): header con acciones "Search files" +
     "Add files" (+) · **medidor de capacidad** (barra fina + "N% of project
     capacity used") · mini-grid 2-col de **doc-cards 148×120px** (título
     clamp, "67 lines", badge de tipo TEXT).
   - **Scheduled** (~75px): "Set up recurring tasks" (og118: N/A fase 1).

### C. Navegación SPA

- Rutas: índice `/projects` → detalle `/project/{uuid}` → chat. Breadcrumb
  regresa; back del browser funciona (history API).
- og118 es Next.js App Router: `app/projects/page.tsx` +
  `app/projects/[id]/page.tsx`, transición client-side sin recarga.

## Capas (framework-first — qué sube a fi-glass, qué se queda en og118)

**fi-glass (primitivas genéricas, cero semántica "project"):**
- `ResourceCardGrid` + `ResourceCard` — el grid del índice (§A.3–A.4):
  título/descripción/timestamp/onClick, hover+active states, auto-rows-fr.
- `ResourceIndexHeader` — título serif + sort + CTA primario (§A.1).
- `ResourceSearchInput` — la búsqueda full-width (§A.2), filtra client-side.
- `WorkspaceDetailLayout` — el split main+rail 577/352 con stack móvil (§B.3).
- `RailPanelStack` + `RailPanel` — el rail de secciones con divisores (§B.5),
  cada panel = {title, actions[], children}.
- `CapacityMeter` — barra + label "N% used" (§B.5 Context).
- `DocCard` — la mini-card de documento 148×120 (título clamp + meta + badge).
- Breadcrumb: evaluar si `AgentWorkspaceShell` ya da el slot; si no, primitivo
  `WorkspaceBreadcrumb`.
- Tests de contrato como los demás primitivos (patrón AgentSidebarSection).

**og118 (consumer):**
- Rutas Next (`app/projects/...`), wiring de `useOg118Projects` al grid,
  upload → `DocCard`s, composer del detalle → crea conversación con
  `corpus_id` del proyecto, breadcrumb copy, branding/tokens.

## Gaps del contrato de datos (server og118) que la página destapa

1. **`GET /projects/{id}/documents` NO existe** — el RAG store sabe listar
   (list_documents MCP) pero no hay superficie HTTP; sin esto el rail de
   Context no tiene qué pintar. Incluir doc_id, título, chunks/lines, fecha.
2. **Project = `{id, name, owner}` pelón** — faltan `description`,
   `instructions` (per-project system prompt), `created_at`/`updated_at`
   (la card muestra "Updated X ago" y el sort es por eso).
3. **Las conversaciones no guardan `project_id`** — la lista "Recents" del
   detalle necesita filtrar conversaciones por proyecto (hoy el binding
   corpus↔turno es efímero, per-request). Extender ConversationStore.
4. **Capacidad**: el meter necesita un dato (bytes o chunks del corpus vs cap).
5. (claude.ai extra, fase 2+): pin/star de proyectos, archive, instructions
   editor modal.

## Canonical path to reuse (Art. 6)

- ComposerFrame, ActionMenu, useInlineRename, ChatFilePreview/UploadStatus,
  sidebarItemStyle hover states — ya existen en fi-glass; la página los
  consume, NO se duplican.
- El patrón de secciones del rail rima con AgentSidebarSection — evaluar
  extracción compartida antes de crear RailPanel desde cero.
- Los tokens de glass-chat (surface-1/2, radius, divisores) ya están en
  glassTheme — la card usa esos, no hexes nuevos.

## The decision that's the owner's

- ¿La página índice REEMPLAZA la sección Projects del sidebar o conviven
  (sidebar = atajo, página = gestión)? claude.ai tiene ambas (nav item →
  página). Propuesta: conviven; el sidebar section se adelgaza a nav + activo.
- ¿Instructions per-project en fase 1 o fase 2? (toca PERSONA/prompt layering
  del server, no solo UI).

## Status / next step

Not built. Next: (1) PR server — los 4 gaps del contrato de datos;
(2) PR fi-glass — primitivas con tests; (3) PR og118 — rutas + wiring.
Fuentes de la investigación: superficie viva claude.ai (medida con DevTools
2026-07-14, sesión real) · help center oficial
https://support.claude.com/en/articles/9517075-what-are-projects ·
https://support.claude.com/en/articles/9519177-how-can-i-create-and-manage-projects

Ver [[framework-first-canary]], [[mobile-viewport-ux]] (la página respeta los
presupuestos móviles), [[og118-milestones-roadmap]].

## PR 1 de 3 — el contrato del server, cerrado (2026-08-22)

Los cuatro huecos que esta tarjeta destapó ya no bloquean nada. El *next step*
decía "(1) PR server — los 4 gaps"; esto es ese PR.

| Hueco | Cómo quedó |
|---|---|
| 1. `GET /projects/{id}/documents` no existía | existe, y devuelve **documentos + capacidad en la misma respuesta** — el rail dibuja el medidor justo encima del grid, así que partirlo en dos rutas sólo compraba un round-trip extra y una ventana donde los dos se contradicen |
| 2. project pelón | `description`, `instructions` y `updatedAt` en el record, más `PATCH /projects/{id}` para poder setearlos y `GET /projects/{id}` para el detalle |
| 3. conversaciones sin `project_id` | `projectId` en el contrato **y en `SUMMARY_FIELDS`**, más `GET /conversations?projectId=` para el "Recents" |
| 4. sin cifra de capacidad | `capacity: {docs, chunks, bytes, maxDocs, maxBytes}` |

**La primitiva de la capacidad subió a fi-runner**, no se resolvió en og118:
`RagStoreClient.quota()` devuelve los techos (`FI_RAG_MAX_DOCS`/`MAX_BYTES`)
porque `stats()` ya daba el numerador y la alternativa era que el consumidor
metiera la mano en `_rag`, un atributo privado cuya forma es asunto de fi-core.

**`null` en `maxBytes`/`maxDocs` significa SIN TOPE**, y el cliente tiene que
decirlo con palabras: pintar un porcentaje contra un techo inventado convierte
un "ilimitado" honesto en un número tranquilizador que nadie puede accionar.

### Decisiones que se tomaron al construir

- **`PATCH`, no `PUT`.** Un campo omitido se deja en paz; un string vacío lo
  borra. Con `PUT` el primer cliente que olvidara reenviar un campo lo borraría
  en silencio.
- **Backfill en LECTURA, no migración.** Un proyecto de antes de este contrato
  se hidrata al leerse (`updatedAt` cae a `createdAt` — la única respuesta
  honesta: nada lo ha tocado desde que nació). Reescribir el JSON entero al
  arrancar tiene un blast radius muchísimo mayor que un merge de diccionario.
- **Subir un documento hace `touch` del proyecto.** Alimentar un proyecto ES
  actividad; sin eso el índice ordenaría uno recién alimentado por debajo de
  otros sin tocar en semanas.

### Lo que NO hace, y hay que decirlo

**`instructions` se guarda pero todavía no lo lee nadie.** Es el campo del
contrato, no el system prompt per-project funcionando: el turno no lo consume.
Cablearlo toca el layering de persona/prompt del server y sigue siendo la
segunda decisión abierta de esta tarjeta (¿fase 1 o fase 2?). Guardar un campo
que nada consume es deuda si se olvida, así que queda escrito aquí.

Tampoco se tocó el hueco 5 (pin/star, archive, editor modal de instructions) —
la propia tarjeta lo puso en fase 2+.

### Verificación

19 tests nuevos en `og118/server/tests/test_projects_contract.py` (incluidos
tres de aislamiento entre cuentas: otra cuenta recibe 404, nunca 403) y 3 en
`fi-runner/tests/test_rag_quota.py`. **Cuatro mutaciones probadas en rojo**:
quitar el `touch` de `updatedAt` en el PATCH, quitar el chequeo de propiedad de
`/documents`, sacar `projectId` de `SUMMARY_FIELDS`, y quitar el backfill de los
records legacy. Suites: og118 **202**, fi-runner **306**, fenix **68**.

### Sigue

(2) PR fi-glass — las primitivas con tests; (3) PR og118 — rutas y wiring. Y
las dos decisiones del dueño siguen abiertas: si el índice reemplaza la sección
del sidebar o conviven, y si `instructions` se cablea en fase 1.

## PR 2 de 3 — las primitivas de fi-glass (2026-08-22)

Viven en `apps/packages/fi-glass/src/resource/`, exportadas por la raíz y por el
subpath `fi-glass/resource`. Se construyeron en el orden que esta tarjeta pidió:
primero el framework, después el consumidor.

| Primitiva | Qué es |
|---|---|
| `ResourceIndexHeader` | título + slot de orden + slot de CTA (§A.1) |
| `ResourceSearchInput` + `filterByQuery` | la búsqueda full-width y su regla de match (§A.2) |
| `ResourceCardGrid` + `ResourceCard` | el grid semántico y la card (§A.3–A.4) |
| `WorkspaceDetailLayout` | el split main + rail de 352px, que APILA en móvil (§B.3) |
| `RailPanelStack` + `RailPanel` | el rail de secciones con divisores (§B.5) |
| `CapacityMeter` | la barra de capacidad (§B.5 Context) |
| `DocCard` + `DocCardGrid` | la mini-card de documento y su grid (§B.5) |
| `WorkspaceBreadcrumb` | §B.1 — se verificó primero que `AgentWorkspaceShell` no diera el slot (Art. 6); no lo da |

### Las decisiones que se tomaron construyendo

- **`CapacityMeter` se niega a dibujar una barra cuando `max == null`.** No
  existe un porcentaje de "ilimitado". Le pasa `null` al render del label para
  que el consumidor escriba palabras reales en vez de una fracción contra un
  techo inventado — es la misma honestidad que el contrato del server, y
  inventarla aquí la lavaría de vuelta a un número. `max === 0` **no** es
  ilimitado: no cabe nada, así que es 100%.
- **`ResourceCard` es un `<a>` de verdad cuando recibe `href`**, y un `<button>`
  si no. No es cosmético: un link real se abre en pestaña nueva, se clickea con
  el botón de en medio y muestra su destino — todo lo que un div-con-onClick
  tira a la basura.
- **Los grids son `<ul>`/`<li>` con nombre accesible**, para que un lector de
  pantalla pueda contar y recorrer.
- **Los divisores del rail salen de una regla de adyacencia en CSS**, no de un
  prop: al primer panel nunca se le pregunta si es el primero.
- **El rail APILA bajo la columna principal** bajo el breakpoint canónico
  (`FI_MOBILE_QUERY`, no un literal retecleado): un rail de 352px al lado de una
  conversación en un teléfono de 390px no deja ninguna de las dos usable.
- **`filterByQuery` pliega acentos**: escribir "papeleria" tiene que encontrar
  "Papelería". Un `includes` ingenuo le contesta "sin resultados" a una búsqueda
  obviamente correcta.

### El guard que hace cumplir la regla dura de esta tarjeta

`noProductNouns.test.ts` lee el código del módulo y falla si aparece
`project`/`proyecto`/`conversation`/`chat`/`corpus` en la API. La regla estaba
escrita sólo en prosa, y una regla que sólo vive en prosa se va: el primer
`newProjectLabel` metido con prisa pasaría review porque nada lo revisa.

**La primera versión del guard no servía y la mutación lo probó:** usaba `\b`, y
`newProjectLabel` no tiene frontera de palabra antes de `Project`, así que el
prop exacto que el guard existe para rechazar pasaba en verde. Ahora matchea
substring. Los tokens `--glass-chat-*` se excluyen antes de revisar: son el
namespace de diseño del propio framework, y un guard que los marcara se
desactivaría por ruido en una semana.

### Verificación

**57 tests** en `src/resource/` (545 en fi-glass completo), typecheck limpio,
`pnpm build` regenerado con el `dist/` **commiteado** (per
[[committed-dist-artifacts]] — este paquete publica su build), `'use client'`
sobrevive al bundle, y `og118-web` sigue compilando contra el fi-glass nuevo.

Mutaciones en rojo: el prop con el sustantivo del consumidor · un string por
defecto en español dentro del código · el medidor inventando un techo sin cuota ·
la card dejando de ser un anchor real.

**Lo que NO se puede afirmar todavía:** la medición a 374px que exige
[[mobile-viewport-ux]]. jsdom no hace layout y aún no hay página que renderice
esto. Lo que sí quedó fijado es que la regla de apilado existe y cuelga del
breakpoint canónico; **la medición en Chrome es del PR 3**, cuando haya una
superficie real que medir.

### Sigue

PR 3: `app/projects/page.tsx` y `app/projects/[id]/page.tsx` en og118,
consumiendo estas primitivas y las rutas del server — y ahí sí, la medición del
render a 374px.

## PR 3 de 3 — la página en og118, y la medición (2026-08-22)

`/projects/` existe, consume las primitivas del PR 2 y las rutas del PR 1.

### La ruta NO pudo ser `/project/{uuid}`, y por una razón dura

og118 es **static export** (`output: 'export'`). Un segmento de filesystem
`projects/[id]` exige `generateStaticParams` en build time, imposible para ids
que se acuñan por cuenta en runtime. Emitir el segmento sin params seguiría
funcionando al hacer click DENTRO del SPA y daría **404 real en el SWA** a quien
recargue o abra un link compartido, porque no hay `staticwebapp.config.json` con
fallback.

Solución: **una ruta estática con `?p=<id>`**, navegada con `history.pushState` y
un listener de `popstate`. Deep-linkable, el botón Atrás camina índice ⇄ detalle,
y cero cambios de infra. La forma de path que pedía esta tarjeta requeriría
cambiar el modelo de deploy de la app que Bernard usa a diario — no vale el
canje por unos caracteres en la URL.

### El hueco 4 recién ahora es real de punta a punta

El PR 1 le enseñó al server a guardar `projectId`, pero nadie se lo mandaba: el
binding del corpus seguía siendo por request. Ahora el record lo lleva
(`ConversationRecord.projectId` en el core, estampado por
`useConversationLibrary`), así que "Recents" tiene qué listar.

**El sello es sólo al NACER, y un test encontró que mi primera versión no lo
era.** Escribí `prevForTitle?.projectId ?? projectId`, que se lee igual y está
mal: una conversación empezada sin proyecto **adoptaba** el que se seleccionara
después, re-archivando en silencio un hilo que nadie movió. El discriminante
correcto es la existencia del record, no si trae valor.

### Lo que la MEDICIÓN encontró (y jsdom no podía ver)

Prometido en el PR 2, hecho aquí. Harness efímero + iframes de 390/374/320 en el
Chrome de debug (que vive en **9333**, no 9222 — el diagnóstico lo halló sin
matar nada).

La primera pasada salió **roja**: las migas del breadcrumb medían **20px**, el
buscador 40, el CTA 37, "Editar" 34 y el select 30 — todos bajo el mínimo de 44
que exige [[mobile-viewport-ux]], y ninguno detectable desde un test unitario.
Arreglado en las dos capas: fi-glass compone `withTouchTarget` en las migas y
sube el buscador bajo `FI_TOUCH_QUERY`; og118 hace lo propio con sus controles.

Segunda pasada, los tres anchos: **cero overflow, cero scroll horizontal, cero
controles bajo 44px**, grid a una columna y rail apilado.

### Lo que NO se hizo, y por qué

- **Sin panel de Instructions.** El campo se guarda y se puede editar por API,
  pero **el turno todavía no lo lee**. Un editor para un campo que el agente
  ignora es una promesa que el producto no cumple. Sale cuando se cablee el
  layering de prompt — sigue siendo decisión abierta del dueño.
- **Sin composer en la página.** El detalle ofrece "Nueva conversación", que
  selecciona el proyecto y lleva al chat: el mismo RESULTADO (una conversación
  nueva ligada al proyecto), sin el composer en sitio. Fase 2.
- Índice y sidebar **conviven**, como esta tarjeta proponía; el sidebar ganó un
  enlace "Ver todos los proyectos →".

### Verificación

core **93**, fi-glass **550**, og118-web **78**; `check:og118-css` al día;
`dist/` de core y fi-glass reconstruido y commiteado; `/projects` se prerenderiza
estático. Mutaciones en rojo: el sello del proyecto convertido en "siempre el
activo", el `??` que yo mismo había escrito mal, `summarize` sin `projectId`, el
mínimo táctil quitado del buscador y de las migas.

## Fase 2a — `instructions` cableadas al prompt (2026-08-22)

El campo llevaba dos PRs guardado y editable **sin que nadie lo leyera**. Ya no.

**No se inventó una capa.** El Runner tiene UNA costura por turno
(`context_prompt`) y los runners están cacheados por elemento, así que meter las
instrucciones en la persona habría sido la capa equivocada: se re-armaría el
runner por proyecto y se invalidaría la caché.

- `owner_instructions_binding()` en fi-runner, con su texto en
  `prompts/owner_instructions_binding.md` (P0: los prompts son contenido).
- `compose_bindings()`, porque el Runner sostiene **un** `context_prompt` y ya
  había otro (`active_corpus_binding`). Junta los addenda y **contiene el fallo
  de uno**: el Runner trata un `context_prompt` que truena como "sin addendum
  ninguno", así que sin esto una excepción en un binding borraría en silencio el
  binding del corpus y el agente dejaría de buscar en el proyecto.
- Orden: corpus primero, dueño al final — lo del dueño queda más cerca del
  mensaje del usuario.

**El texto va ENMARCADO, no concatenado.** El modelo no tiene otra forma de
distinguir las palabras del dueño de las del framework, y un párrafo que abra
con "ignora lo anterior" se leería como si lo hubiera dicho el sistema. La
plantilla dice de quién es, lo cerca entre marcadores y declara que está
subordinado a las reglas de seguridad y a la tool policy.

**De dónde salen es lo que importa: del REGISTRY, jamás del request.** Un cliente
que pudiera mandar su propio texto se estaría entregando a sí mismo un system
prompt. `ChatRequest` no tiene ese campo y pydantic tira los extras; la única vía
es `PATCH /projects/{id}`, que exige propiedad. Hay test para las dos mitades.

**Tope de 4000 caracteres**, en dos capas: fi-runner **trunca** (el dueño
conserva el principio de lo que escribió, nunca se le quita todo en silencio) y
og118 **rechaza antes** con `INSTRUCTIONS_TOO_LONG`, porque un documento pegado
empuja la persona y los guards al borde de la ventana, que es donde los modelos
empiezan a soltarlos.

**Y recién ahora se shippeó el editor.** Estuvo fuera a propósito mientras el
campo sólo se guardaba; un editor para un ajuste que el agente ignora es una
promesa que el producto no cumple.

### Verificación

fi-runner **325**, og118 **211**, fenix **68**, og118-web **78**. Medido en
Chrome a 390/374/320 en los dos estados del panel: cero overflow, cero scroll
horizontal, cero controles bajo 44px — y de paso cazó el `input` del nombre en
42px, que la medición del PR 3 no vio porque nunca abrió el estado de edición.

Mutaciones en rojo: el combinador sin contención · el truncado quitado · el
context leyendo del request en vez del registry · el tope del PATCH quitado.
