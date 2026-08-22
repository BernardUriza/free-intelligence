# B3-FIGLASS-CONVERSATION-RENAME-1 — editable chat names in fi-glass

Status: **Done** — shipped, con tests y consumido por og118 (verificado 2026-08-22)
Proposed: 2026-06-24 by Bernard

## What it is

Let a user **rename a conversation** (edit its chat title) from the sidebar.
Bernard greenlit it explicitly ("la quiero") and ruled it must be built **directly
in fi-glass**, NOT consumer-local in og118 — renaming a conversation is universal
local-first chat state (title, edit, persistence, selection, list, UX), so a
consumer-local version means the next wrapper pays for it again
([[framework-first-canary]]).

## Canonical path to reuse (Art. 6)

Build the primitive in **fi-glass**; og118 is the **first consumer / canary**.
The orchestrator coagent's proposed contract (2026-06-24):

- Primitive: `ConversationTitleEditor` (or a capability folded into
  `ConversationListItem`).
- Contract: `title`, `fallbackTitle`, `isEditing`, `onRename(conversationId, title)`,
  `onCancel`, `maxLength`, `emptyTitlePolicy`, optimistic/local-first update,
  persistence in the conversation library, keyboard UX (Enter confirms, Escape
  cancels, blur confirms-or-cancels per an explicit decision), a11y labels.
- Persistence rides the **identity-scoped IndexedDB conversation library** already
  shipped for #276 (`free-intelligence-conversations--<sub>`) — so a rename
  persists scoped per identity and never crosses accounts.

## Acceptance criteria (from the coagent)

- Rename a conversation from the sidebar.
- Persists in IndexedDB scoped by identity; does NOT cross accounts.
- Does not lose selection; does not break mobile tap targets.
- Does not delete the transcript; uses no prompt/model; touches no backend.

## The decision that's the owner's

- `emptyTitlePolicy` and the blur behavior (confirm vs cancel on blur) — pick one
  explicitly before building.
- Sequencing: the coagent recommends closing the **#276 cross-account smoke first**
  (it needs Bernard's 2nd-account login), THEN building rename. Bernard's call
  whether rename goes before or after that smoke.

## Status / next step

Accepted, not built. Sits within the broader fi-glass-descent roadmap the coagent
laid out (see the report / [[b3-figlass-shell-primitives]] for the sibling list:
resource-list-item primitives, composer-editable-while-streaming, identity-scoped
store formalization, finite agent roster). This item is the P0 of that list.

Related: [[framework-first-canary]], [[b3-figlass-shell-primitives]],
[[og118-identity-scoping-leak]].

## Cierre verificado (2026-08-22)

Construido en fi-glass como mandaba la regla, con og118 de canario — no
consumer-local.

- Primitiva: `apps/packages/fi-glass/src/agent/AgentSidebarItem.tsx:132`
  `useInlineRename(value, onRename, {maxLength, emptyPolicy})` y `:292`
  `EditableResourceItem`. Exportadas en `src/agent/index.ts:89`.
- **Las dos decisiones del dueño quedaron tomadas y codificadas:** Enter
  confirma, Escape cancela, **blur confirma** (`:181`), con un `cancelledRef`
  (`:139`) para que el blur que sigue a Escape no re-confirme el borrador que se
  acaba de tirar. `emptyPolicy` es `'revert' | 'keep'`, default `revert`: título
  vacío llama `onRename('')` y la librería vuelve a derivar el automático
  (`:105`).
- Persistencia: `useConversationLibrary.ts:65` → `renameConversationRecord` de
  `@free-intelligence/core`, con `titleCustom` (`:162`) para que un título puesto
  a mano sobreviva a los mensajes siguientes. El scoping por identidad lo hereda
  de la IndexedDB por `sub` (`useIndexedDBConversationLibrary.ts:26`).
- a11y: `renameLabel` y `renameInputLabel` son props **requeridas** (`:284`); el
  trigger hace `stopPropagation` para que renombrar nunca robe la selección.
- Tests: `AgentSidebarItem.test.tsx:140` (6 casos) y
  `useConversationLibrary.test.ts:56` (4 casos).
- Consumido: `apps/og118/web/components/Og118Sidebar.tsx:114` y
  `Og118AgentChat.tsx:238`.

Los cuatro criterios de aceptación se cumplen.
