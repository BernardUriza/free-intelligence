# B3-FIGLASS-SHELL-PRIMITIVES-1 — extract sidebar/resource/composer layout primitives to fi-glass

Status: Proposed
Proposed: 2026-06-23 by Bernard (via coagent review of og118 globals.css size)

## What it is

og118's `apps/og118/web/app/globals.css` is 454 LOC / 57 selectors, and ~44 of
them are **pure layout of structures that are already components**: `og-sidebar*`
+ `og-chat*` (conversation list/rows), `og-projects*` + `og-project*` (resource
section/items), `og-send*` / `og-mic*` / `og-composer*` (composer action slots).
Only ~3 blocks are tokens/branding. The size is a **framework-leak tell**
([[framework-first-canary]] / DD-002-LESSON): reusable shell anatomy got trapped
as flat CSS in the consumer instead of rising to fi-glass as token-themed
primitives. The next shell (slate/paper) would re-write these 44 selectors from
scratch — paying twice (Art. 6).

The goal is NOT "fi-glass looks like og118" / copying og-* CSS up. The goal is
fi-glass offering **slots + layout contracts** so og118/slate/paper never
re-implement the same skeleton.

## The line — fi-glass vs consumer (coagent's classification)

**Rises to fi-glass** (reusable structure): sidebar rail layout; conversation
list; conversation row; section header; list empty-state; item action slot;
active/selected row state; destructive action slot; "resource group list" generic
pattern (Projects is one instance); composer action rail; composer
primary/secondary action slots; mobile touch-target integration; spacing/gap/
layout; responsive drawer behavior. Candidate (semantic, NOT og-*) names:
`AgentSidebar`, `AgentSidebarSection`, `AgentSidebarItem`, `AgentResourceSection`,
`AgentResourceItem`, `ComposerActionSlot`, `ComposerToolbar`, `AgentShellRail`.

**Stays in og118** (product semantics): what a Project is; how it's created;
upload lifecycle; project/corpus binding; exact business copy + labels ("Projects",
"Nuevo chat"); branding iconography; Projects-above/below decision; handlers
(`onNewChat`/`onDelete`/`onSelectProject`); Auth0/account state; permissions;
Projects localStorage schema. I.e. fi-glass knows how to render a resource list
with actions; og118 decides those resources are projects and what they do.

## Canonical path to reuse (Art. 6)

Extract incrementally into `apps/packages/fi-glass`, consumer consumes the
primitives. Recommended extraction order: (1) `AgentSidebarSection` /
`AgentSidebarItem`; (2) conversation list consumes them; (3) projects section
consumes the same pattern; (4) composer action slots; (5) delete og118 dead CSS.
**Every PR must REDUCE og118 CSS, not just move it.**

Acceptance — good PR: og118 CSS drops; fi-glass gains a reusable primitive;
slate/paper could use it with zero og118 knowledge; consumer keeps
labels/actions/data; no CSS against fi-glass-internal DOM; no mobile/desktop
regressions. Bad PR: fi-glass receives og-* classes; og118 colors/branding copied
up; Projects becomes a global fi-glass concept; layout primitives mixed with
auth/upload/corpus.

## The decision that's the owner's

Priority/timing. The coagent is explicit: **NOT now** — this is a separate arc
**after** the security + RAG work, and must not compete with two security bugs and
a broken RAG. Do not open it until closed: #277 (filesystem exposure) deploy +
exploit smoke; #276 (identity-scoped stores) deploy + account-isolation smoke;
RAG lock/perms + retrieval smoke; [[fi-runner-toolpolicy-1-companion-profile]].

## Status / next step

First step DONE: `B3-FIGLASS-SHELL-PRIMITIVES-AUDIT-1` — the read-only audit (all
47 selectors classified, mapped to component + target primitive, incremental PR
plan 1A→1D) is complete in [[b3-figlass-shell-primitives-audit]] (2026-06-24).
Key finding: `og-chat-item` and `og-project-item` are structural twins (the
un-fakeable proof the item primitive is real), and the #283 rename already
sedimented the inline-edit affordance (`og-chat-item-rename*`) that belongs in
`EditableResourceItem`. ~30 reusable selectors vs ~12 product + ~8 tokens; 0 dead
families.

Remaining: open the FIRST extraction PR, `B3-FIGLASS-SHELL-PRIMITIVES-1A`
(`AgentSidebarItem`/`EditableResourceItem`/`ItemActionSlot`/`DestructiveActionSlot`,
canary = og118 conversation list). Security gate is CLEAR (2026-06-24); the only
gate left on the extraction arc is Bernard's greenlight to open 1A. Promote this
item to *In progress* when he does.

Read-only audit first cut (2026-06-24, via `/exchange-coagent`): fresh inventory of
`globals.css` is now **486 LOC / 47 unique `og-*` selectors** (was 454/57). Families:
`og-chat` ×18 (conversation list/rows → `AgentSidebarItem`/`EditableResourceItem`),
`og-project` ×9 + `og-projects` ×7 (resource section → `AgentResourceItem`/`Section`),
`og-sidebar` ×7 (rail → `AgentSidebarSection`), `og-send` ×4 + `og-mic` ×4 +
`og-composer` ×3 (composer slots → `ComposerActionSlot`), `og-voice` ×8 + `og-auth` ×5
(product-specific, stay in og118). The rename (#283) ADDED `og-chat-item-rename-btn`,
`og-chat-item-rename`, `og-chat-item-title` — i.e. it sedimented MORE consumer-local
layout that belongs in fi-glass (`EditableResourceItem` + `ItemActionSlot` + title
slot), confirming the framework-leak thesis. Security gate now CLEAR — #277, #276, AND
RAG lock/perms + retrieval smoke all closed 2026-06-24 (29 tests green: H5 fcntl lock,
filesystem perms on /opt/fi/data non-root, HTTP corpus-ownership enforcement, ingest→
search smoke). The extraction arc is now only Bernard's timing call, no security blocker.

Partial groundwork already shipped this session (2026-06-23): `Og118AgentChat.tsx`
507→227 LOC via `useOg118VoiceComposer` + `Og118AuthBanner` +
`Og118VoiceErrorBanner` extraction, and banner/mic inline styles moved to og-*
classes + tokens — but those classes still live in the **consumer**; this item is
about lifting the *structure* into fi-glass.

Related: [[framework-first-canary]], [[b3-og118-mobile-responsive-shell]],
[[proj-sync-1-backend-owned-projects]].
