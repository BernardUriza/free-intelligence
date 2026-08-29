# Backlog — Free Intelligence

One markdown file per item. Status flips the day it changes (no fake-green).

**Auditoría del 2026-08-23:** cada tarjeta se re-verificó contra el CÓDIGO, no
contra su propia línea `Status:`. La del 2026-08-22 había encontrado cinco
entregadas mal marcadas; ésta encontró **cinco más** — tres shipeadas hace
semanas sentadas en la tabla equivocada, y dos entregadas a medias etiquetadas
como "Proposed". El índice vuelve a mentir en cuanto alguien cierra una tarjeta
sin tocarlo, así que **cerrar una tarjeta incluye editar este archivo**.

## Abiertas

| Item | Status | Propuesta |
|---|---|---|
| [OG118-BACKGROUND-1 — ejecución real en background (que "te aviso" sea verdad)](og118-real-background-execution.md) | **Not built** — esperando una decisión de arquitectura de Bernard | 2026-07-05 |
| [B3-FIGLASS-SHELL-PRIMITIVES-1 — extraer sidebar/resource/composer a fi-glass](b3-figlass-shell-primitives.md) | **Parcial** (verificado 2026-08-23) — 1A y 1C entregados y consumidos por og118; faltan los slots del composer. El criterio de aceptación se movió al revés: `globals.css` pasó de 391 a 820 LOC | 2026-06-23 |
| [B3-AURITY-REACT19-REFS-1 — errores latentes de ref-type de React 19 en aurity](b3-aurity-react19-refs.md) | **Casi cerrada** (verificado 2026-08-23) — 7 de los 8 murieron solos al subir `@types/react` a 19.2.16; queda `NeuralNetworkCanvas.tsx:20`. aurity sigue sin gate de tipos (`ignoreBuildErrors: true`) | 2026-06-19 |
| [OG118-IOS-SWIFT62-1 — SE-0461 sube el decode al main actor al migrar a Swift 6.2](og118-ios-swift62-se0461.md) | **Not built** (verificado 2026-08-23) — `SWIFT_VERSION` sigue en 5.9, sin strict-concurrency ni `@concurrent`. Es la vacuna para el día del upgrade, no deuda de hoy | 2026-08-13 |
| [Gate 3 — Auth0 (+ Google social) para cuentas de og118](gate3-auth0-google.md) | Accepted | 2026-06-20 |

## En curso

| Item | Status | Propuesta |
|---|---|---|
| [OG118-IOS-1 — cliente nativo de iPhone (SwiftUI)](og118-ios-tracer.md) | **In progress** (re-verificado 2026-08-23) — compila, arranca y pinta el login en simulador. Falta la primera vuelta de chat real. ⚠️ `apps/og118-ios/README.md:131-136` sigue diciendo "bloqueado: falta Xcode", que su propia tabla desmiente | 2026-08-12 |
| [AIREBACKEND-1 — el backend propio siempre-arriba y observable](fi-runner-aire-backend.md) | **In progress** (re-verificado 2026-08-23) — sólo queda que `tool_policy` viaje al backend; el propio `aire.py:45` lo declara como el único hueco | 2026-07-13 |

## Entregadas

| Item | Status | Propuesta |
|---|---|---|
| [CONV-CONCURRENCY-1 — pin/título se perdían en last-write-wins entre dispositivos](og118-conv-concurrency.md) | **Done 2026-08-23** — `PUT` deja de opinar sobre las banderas y `PATCH` manda el delta; la ruta del 409 sobre `updatedAt` resultó incorrecta y la tarjeta explica por qué | 2026-07-13 |
| [FIGLASS-PROJECTS-PAGE-1 — Projects como página (paridad claude.ai)](figlass-projects-page.md) | **Done 2026-08-22** — los 3 PRs + `instructions` cableadas al prompt. Fase 2: composer en la página, pin/archive de proyectos | 2026-07-14 |
| [OG118-SESSION-DELETE-CASCADE-1 — borrar conversación borra su sesión nativa](og118-session-store-delete-cascade.md) | **Done 2026-08-22** — cascada en las dos superficies de borrado. Queda el TTL de los huérfanos que el bug ya dejó | 2026-07-13 |
| [RESONANCE — modo llamada de voz sin pantalla](og118-resonance-voice-mode.md) | **Done** (verificado 2026-08-23) — máquina de llamada, barge-in, VAD y hangup por inactividad en fi-glass, consumidos por og118. Residual: sigue tras el flag `?resonance=1` | 2026-06-29 |
| [CONVO-SYNC-1 — conversaciones server-side](convo-sync-serverside-conversations.md) | **Done** (verificado 2026-08-23) — `ConversationStore` + CRUD + `RemoteConversationLibrary` cloud-autoritativo; la bifurcación "dual vs sólo server" se decidió como dual. Residuales: ventana de 20 msgs/16k y el prompt-cache env-gated | 2026-06-21 |
| [og118 Projects — espacio de negocio de la papelería](og118-projects-papeleria-business.md) | **Done** (verificado 2026-08-23) — upload + corpus por turno + `active_corpus_binding` (el "hueco de framework" subió a fi-runner). La vertiente papelería quedó DROPPED por el ToS del OAuth personal | 2026-06-19 |
| [OG118-LIVING-CLAUDE — un CLAUDE.md por chat que el agente reescribe](og118-living-claude-per-chat.md) | Done 2026-08-21 (PR #411, verificado en vivo) | 2026-08-21 |
| [FI-RUNNER-MULTIMODAL-1 — imagen/documento como primitiva del turno](fi-runner-multimodal-turn.md) | **Done** — shipped como `images: list[TurnImage]` (verificado 2026-08-22) | 2026-07-05 |
| [B3-FIGLASS-CONVERSATION-RENAME-1 — nombres de chat editables en fi-glass](b3-figlass-conversation-rename.md) | **Done** — con tests y consumido por og118 (verificado 2026-08-22) | 2026-06-24 |
| [PROJ-SYNC-1 — hidratación de proyectos desde el servidor](proj-sync-1-backend-owned-projects.md) | **Done** — falta sólo el flag de staleness (verificado 2026-08-22) | 2026-06-21 |
| [FI-RUNNER-TOOLPOLICY-1 — perfil "companion" de herramientas](fi-runner-toolpolicy-1-companion-profile.md) | **Done** — `ToolPolicy.companion()`; residual: subir `tools=` al framework (verificado 2026-08-22) | 2026-06-21 |
| [OG118-ELEMENTOS — 118 personas nombradas (tabla periódica, tope duro)](og118-elementos-118-gpt-personas.md) | **Done** (estructura) — 3 activos de 118; falta curación (verificado 2026-08-22) | 2026-06-24 |
| [B3-FIGLASS-SHELL-PRIMITIVES-AUDIT-1 — auditoría read-only de `globals.css`](b3-figlass-shell-primitives-audit.md) | Done (2026-06-24, auditoría; hija de B3-FIGLASS-SHELL-PRIMITIVES-1) | 2026-06-24 |
| [B3-OG118-MOBILE-1 — shell responsive / drawer móvil](b3-og118-mobile-responsive-shell.md) | Done (2026-06-30) | 2026-06-19 |
| [B3-FIGLASS-UX-DISTRIBUTION-1 — contratos de distribución](b3-figlass-ux-distribution.md) | Done — 6/6 (#306-312) | 2026-06-30 |
| [OG118-EXTERNAL-CORPUS-GAP-1 — elementos externos ignoraban el Project activo](og118-external-elements-corpus-gap.md) | Done (2026-07-14, RAG server-side) | 2026-07-14 |
| [fi-core — a corrected document leaves its old chunks retrievable](b3-fi-core-retriever-reingest-stale.md) | Proposed — reproduced; the obvious fix removes zero rows, so the route is a design call | 2026-08-24 |
| [fi-core: ClinicalDomain con señales pesadas y bilingües](fi-core-weighted-clinical-domain.md) | In progress — fase fi-core shippeada en 0.26.0 (SignalGroup/WeightedSignals, corpus migrado verbatim + 4 categorías nuevas); falta consumo en discord-bot; el cierre del #52 de Alex es la lista de requisitos (pesos, inglés, los 5 regex, 4 categorías sin detección). SignalGroup pesado en fi_core.cognitive → el corpus local de discord-bot muere con grep | 2026-08-28 |
| [og118 Proyectos — escondido tras `OG118_PROYECTOS`](og118-proyectos-tras-flag.md) | **Dropped 2026-08-29** — apagado por default, no borrado (Bernard lo retoma después). Las rutas no se montan, `rag_store` sale del turno, `corpus_id` se ignora. Las DOS ramas cubiertas por tests, que fue la condición: una rama apagada sin tests se pudre. Dos huecos si vuelve: la frontera del corpus y `delete_corpus` auto-aprobado | 2026-06-19 |
