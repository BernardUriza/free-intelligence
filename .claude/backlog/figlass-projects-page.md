# FIGLASS-PROJECTS-PAGE-1 — Projects como PÁGINA (paridad claude.ai), primitivas en fi-glass

Status: Proposed
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
