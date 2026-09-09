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
| [OG118-IOS-SWIFT62-1 — SE-0461 sube el decode al main actor al migrar a Swift 6.2](og118-ios-swift62-se0461.md) | **Not built** (verificado 2026-08-23) — `SWIFT_VERSION` sigue en 5.9, sin strict-concurrency ni `@concurrent`. Es la vacuna para el día del upgrade, no deuda de hoy | 2026-08-13 |

## En curso

| Item | Status | Propuesta |
|---|---|---|
| [OG118-IOS-1 — cliente nativo de iPhone (SwiftUI)](og118-ios-tracer.md) | **In progress** (re-verificado 2026-08-23) — compila, arranca y pinta el login en simulador. Falta la primera vuelta de chat real. README corregido 2026-09-09 | 2026-08-12 |

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
| [OG118-ELEMENTOS — 118 personas nombradas (tabla periódica, tope duro)](og118-elementos-118-gpt-personas.md) | **Done** (estructura) — 4 activos de 118 (Pu·Reaper local, 2026-09-08); falta curación | 2026-06-24 |
| [B3-FIGLASS-SHELL-PRIMITIVES-AUDIT-1 — auditoría read-only de `globals.css`](b3-figlass-shell-primitives-audit.md) | Done (2026-06-24, auditoría; hija de B3-FIGLASS-SHELL-PRIMITIVES-1) | 2026-06-24 |
| [B3-OG118-MOBILE-1 — shell responsive / drawer móvil](b3-og118-mobile-responsive-shell.md) | Done (2026-06-30) | 2026-06-19 |
| [B3-FIGLASS-UX-DISTRIBUTION-1 — contratos de distribución](b3-figlass-ux-distribution.md) | Done — 6/6 (#306-312) | 2026-06-30 |
| [OG118-EXTERNAL-CORPUS-GAP-1 — elementos externos ignoraban el Project activo](og118-external-elements-corpus-gap.md) | Done (2026-07-14, RAG server-side) | 2026-07-14 |
| [fi-core — a corrected document leaves its old chunks retrievable](b3-fi-core-retriever-reingest-stale.md) | **Done 2026-09-09** — fi-core 0.31.0: un solo camino de escritura (`embed_chunks` + `replace_document`), `source_ref` es el documento; contextualizer alcanzable vía `from_components` | 2026-08-24 |
| [fi-core: ClinicalDomain con señales pesadas y bilingües](fi-core-weighted-clinical-domain.md) | **Done con residuales** (re-verificado 2026-09-08) — fi-core 0.26.0→0.29.1 y consumo en discord-bot #52/#53/#54 (v4.38.15): `vulnerability.py` sin regex ni corpus local (grep → 0). Residuales: H3/H4 del #55, banda en modo observación, y las dos lecturas paralelas → [[fi-core-verdict-carries-matched-groups]] | 2026-08-28 |
| [og118 Proyectos — escondido tras `OG118_PROYECTOS`](og118-proyectos-tras-flag.md) | **Dropped 2026-08-29** — apagado por default, no borrado (Bernard lo retoma después). Las rutas no se montan, `rag_store` sale del turno, `corpus_id` se ignora. Las DOS ramas cubiertas por tests, que fue la condición: una rama apagada sin tests se pudre. Dos huecos si vuelve: la frontera del corpus y `delete_corpus` auto-aprobado | 2026-06-19 |
| [fi-core: `GravityScore.reasons` estructurados — el veredicto explica con nombres de grupo, nunca con la frase](fi-core-urgency-structured-reasons.md) | **Done 2026-09-08** — fi-core 0.30.0 (PR #465): `UrgencyReason(kind, key, weight, term)`, `term` fuera del `repr`, `explain()` conserva la prosa. Consumidor: discord-bot v4.38.18 loguea `kind:key:peso` | 2026-09-08 |
| [fi-core: el veredicto de banda carga sus grupos disparados — `ClinicalDomain.assess()` → `ClinicalVerdict`](fi-core-verdict-carries-matched-groups.md) | **Done 2026-09-08** — fi-core 0.30.0 (PR #465): una lectura, un veredicto; `_GROUP_TO_CONDITION` ya vivía en fi-core como `SignalGroup.category`. Consumidor: discord-bot v4.38.18 colapsó a `crisis_verdict()` | 2026-09-08 |
| [fi-core: primitivas de auditoría — seudónimo HMAC con llave que rota por mes + evento con `audit_hash`](fi-core-audit-primitives.md) | **Done 2026-09-08** — fi-core 0.30.0 (PR #465): `fi_core.audit` (`pseudonym` / `audit_period` / `audited`), byte-compatible con el canary. El repoint de discord-bot `audit.py` es de Alex (#54) | 2026-09-08 |
| [Gate 3 — Auth0 (+ Google social) para cuentas de og118](gate3-auth0-google.md) | **Done** (verificado 2026-09-09) — shipped 2026-06-21 (`fd964ff6` backend, `3a823449` web) y 2026-07-08 (cuentas cloud); app.og118.ai corre en `auth0` sobre el tenant dev compartido, principals `google-oauth2\|…`. La tarjeta llevaba desde junio diciendo *Not built* | 2026-06-20 |
| [B3-AURITY-REACT19-REFS-1 — errores latentes de ref-type de React 19 en aurity](b3-aurity-react19-refs.md) | **Done 2026-09-09** — los 8 muertos (`NeuralNetworkCanvas.tsx:20` hoy); quedan 24 errores de dominio fuera de alcance y `ignoreBuildErrors: true` | 2026-06-19 |
| [AIREBACKEND-1 — el backend propio siempre-arriba y observable](fi-runner-aire-backend.md) | **Done** (cerrada 2026-09-09) — tres cortes shipped; `tool_policy` no se forwardea porque la puerta no tiene campo: es aire-server #37, decisión de Bernard | 2026-07-13 |
| [B3-FIGLASS-SHELL-PRIMITIVES-1 — extraer sidebar/resource/composer a fi-glass](b3-figlass-shell-primitives.md) | **Done 2026-09-09** — 1A/1C/1D entregados; `ComposerActionSlot` cierra los slots del composer, `globals.css` 820 → 771, medido a 374px en Chrome. Lo que queda de `og-*` es la página de Proyectos, otra tarjeta | 2026-06-23 |
