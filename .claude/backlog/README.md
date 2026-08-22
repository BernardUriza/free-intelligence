# Backlog — Free Intelligence

One markdown file per item. Status flips the day it changes (no fake-green).

**Auditoría del 2026-08-22:** cada tarjeta se verificó contra el código, no
contra su propia línea `Status:`. **Cinco** estaban marcadas como pendientes y
ya estaban entregadas — el índice llevaba hasta dos meses mintiendo. Las que
siguen abiertas se re-verificaron y traen la evidencia dentro.

## Abiertas

| Item | Status | Propuesta |
|---|---|---|
| [FIGLASS-PROJECTS-PAGE-1 — Projects como página (paridad claude.ai)](figlass-projects-page.md) | **Not built** — bloqueada por 4 huecos del contrato del server | 2026-07-14 |
| [OG118-SESSION-DELETE-CASCADE-1 — borrar conversación debe borrar su sesión nativa](og118-session-store-delete-cascade.md) | **Not built** — y el borrado en bloque tiene el mismo hueco | 2026-07-13 |
| [CONV-CONCURRENCY-1 — pin/título se pierden en last-write-wins entre dispositivos](og118-conv-concurrency.md) | **Not built** — la carrera sigue intacta | 2026-07-13 |
| [OG118-BACKGROUND-1 — ejecución real en background (que "te aviso" sea verdad)](og118-real-background-execution.md) | **Not built** — esperando una decisión de arquitectura de Bernard | 2026-07-05 |
| [OG118-IOS-SWIFT62-1 — SE-0461 sube el decode al main actor al migrar a Swift 6.2](og118-ios-swift62-se0461.md) | Proposed (sin auditar) | 2026-08-13 |
| [RESONANCE — modo llamada de voz sin pantalla](og118-resonance-voice-mode.md) | Proposed (sin auditar) | 2026-06-29 |
| [og118 Projects — espacio de negocio de la papelería](og118-projects-papeleria-business.md) | Proposed (sin auditar) | 2026-06-19 |
| [B3-AURITY-REACT19-REFS-1 — errores latentes de ref-type de React 19 en aurity](b3-aurity-react19-refs.md) | Proposed (sin auditar) | 2026-06-19 |
| [B3-FIGLASS-SHELL-PRIMITIVES-1 — extraer sidebar/resource/composer a fi-glass](b3-figlass-shell-primitives.md) | Proposed (sin auditar) | 2026-06-23 |
| [CONVO-SYNC-1 — conversaciones server-side](convo-sync-serverside-conversations.md) | Proposed (sin auditar; posiblemente subsumida por PROJ-SYNC-1) | 2026-06-21 |
| [Gate 3 — Auth0 (+ Google social) para cuentas de og118](gate3-auth0-google.md) | Accepted | 2026-06-20 |

## En curso

| Item | Status | Propuesta |
|---|---|---|
| [OG118-IOS-1 — cliente nativo de iPhone (SwiftUI)](og118-ios-tracer.md) | **In progress** — el gate de Apple se levantó; compila, arranca y pinta el login en simulador. Falta la primera vuelta de chat real | 2026-08-12 |
| [AIREBACKEND-1 — el backend propio siempre-arriba y observable](fi-runner-aire-backend.md) | **In progress** — dos cortes entregados; el "gap" de `llm_router_policy.py` era falso. Sólo queda `tool_policy` | 2026-07-13 |

## Entregadas

| Item | Status | Propuesta |
|---|---|---|
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
