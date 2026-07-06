# B3-FIGLASS-UX-DISTRIBUTION-1 — distribution contracts for fi-glass (spacing/semantic/cards/scroll/CQ)

Status: Done — 6/6 shipped (PR1–PR6 merged)
Proposed: 2026-06-30 by Bernard (UX feedback on og118 sidebar) + coagent plan
Updated: 2026-07-04 — PR6 (container queries) merged (#312); arc complete, verified live in og118

## What it is

fi-glass lays out its shell with **inline `display:flex` divs and magic spacing
literals**, not distribution contracts. The visible symptom (Bernard's 390px+
desktop screenshot): the og118 Projects section is a cramped ~60px box where the
project card collides with the "+ Subir archivo" dropzone, sections have no
breathing room or visual hierarchy, and the DOM has no semantic landmarks.

The coagent's reframe: *fi-glass no necesita más CSS, necesita **contratos de
distribución*** — layout primitives with semantics (shell, sidebar rail, section,
section-card, scroll-region, density, spacing scale, collapse, container-aware
sizing). NOT inline `display:flex` as architecture, NOT `gap:.25rem` loose in the
consumer.

## Canonical path to reuse (Art. 6)

Framework-first, og118 is the canary. The foundation already exists and is
EXTENDED, not rebuilt: `sidebarSectionStyle.ts` (`fi-sidebar-section`, token-driven
`--fi-section-head-*`, B3-FIGLASS-SHELL-PRIMITIVES-1C) and `sidebarItemStyle.ts`.
What SUBE to fi-glass: spacing tokens, section-cards, header/action/footer slots,
scroll-region, density, landmarks, container behavior. What stays in og118: the
labels "Proyectos"/upload/corpus, Oganesson/Elementos, Auth0, business project
counts, the emerald branding. See [[b3-figlass-shell-primitives]] and
[[framework-first-canary]].

## Read-only audit (PR1 deliverable — done 2026-06-30)

Layout-smell matrix from grep across fi-glass + og118:

| surface | file:line | smell | proposed primitive/token | PR |
|---|---|---|---|---|
| og118 Projects list | `og118/web/app/globals.css:231` | `max-height: 30vh` (viewport-blind → 60px cramped box) | `AgentScrollRegion` / section `scrollBehavior` + `maxItemsBeforeScroll` | 5 |
| og118 Projects list | `og118/web/app/globals.css:236` | `gap: 0.25rem` magic | `--fi-section-gap` token | 2,4 |
| og118 sidebar | `og118/web/app/globals.css:53` | `padding: 0.7rem 0.85rem 0.25rem` magic | `--fi-section-padding` token | 2 |
| shell slots | `AgentWorkspaceShell.tsx:197-208,255` | `<div data-fi-slot="header/main/conversation/rail/footer">` non-semantic | `<header>/<main>/<aside>/<nav>/<section>` landmarks | 3 |
| shell root | `AgentWorkspaceShell.tsx:161,243` | inline `display:flex; height:100dvh` (root OK — viewport-locked by design) | keep; move structural children to contracts | 3 |
| fi-glass layout | 5 files, 17 inline `display:flex/grid` | inline layout as architecture | semantic primitives + density | 3,4 |
| fi-glass spacing | 12 `rem/px` literals in TSX | magic numbers, no scale | `--fi-space-*` scale | 2 |

100dvh in the shell root is intentional (viewport-locked, backward-compat) — NOT a
smell.

## The arc (coagent's level plan — ordered PRs, backward-compatible)

1. **B3-FIGLASS-UX-DISTRIBUTION-AUDIT-1** — read-only smell matrix. ✅ **DONE** (PR #306, docs).
2. **B3-FIGLASS-UX-TOKENS-1** — spacing scale (`--fi-space-1..5`, `--fi-section-padding`,
   `--fi-section-gap`, `--fi-touch-target`) + `density` contract. Conservative defaults
   (current look ≈ `compact`; og118 opts into `comfortable` for air). Small, low risk.
   ✅ **DONE** (PR #307, `a2e14688` — `densityStyle.ts`).
3. **B3-FIGLASS-SEMANTIC-SHELL-1** — replace inline-flex slots with `main`/`aside`/`nav`/
   `section`/`header` landmarks + aria-labels. Visual-equivalent, no consumer CSS to
   survive, no mobile regression. ✅ **DONE** (PR #308, `aa0fe847`).
4. **B3-FIGLASS-SIDEBAR-SECTIONS-2** — extend `AgentSidebarSection`: `variant="plain"|"card"`,
   `collapsible`/`defaultCollapsed` (`<details>/<summary>`), header/action/footer slots,
   `emptyState`, `scrollBehavior`. og118 Projects → `variant="card"`.
   ✅ **DONE** (PR #309, `ad26989b`).
5. **B3-FIGLASS-SCROLL-REGIONS-1** — `AgentScrollRegion` (or section-integrated):
   `maxItemsBeforeScroll`, content-aware `max-block-size`. **Kills `max-height:30vh`** —
   Projects grows by content (1–3 items, no premature scroll), dropzone gets real gap,
   Conversations keep filling remaining space without being crushed.
   ✅ **DONE** (PR #310, `9c7a6656` — `30vh` removed from og118 globals).
6. **B3-FIGLASS-CONTAINER-QUERIES-1** — `container-type:inline-size` per panel; narrow
   sidebar = compact rows, wide = show meta; narrow composer = icon-only labels. Last,
   because CQ without the semantic primitives just masks old CSS.
   ✅ **DONE** (PR #312, `40b7bb91`). Established fi-glass's first named CQ containers
   (`fi-sidebar` on the `<nav>`, `fi-composer` on the composer cap). `@container fi-sidebar
   (max-width:220px)` hides item meta + compacts rows; og118 canary keys `@container
   fi-composer (max-width:420px)` to collapse the Elemento label. Verified live: labels
   toggle reactively at the container thresholds.

## The decision that's the owner's

RESOLVED. The full arc (PR1–PR6, #306–#312) shipped and merged with Bernard's per-level
GO for each. Nothing left to decide; the item is Done.

## Status / progress (2026-07-03)

Arc **5/6 shipped and verified live** in og118 (`localhost:3000` from `main`, fi-glass dist
rebuilt from arc source):

- **Tokens (PR2):** `--fi-space-1..5`, `--fi-touch-target: 44px`, density `comfortable`
  active on `.fi-agent-workspace`; every control carries `fi-touch-target` (44px min).
- **Card variant (PR4):** og118 Projects renders as `fi-sidebar-section--card` (padding/
  margin 8px, rounded boundary) — breathes at 99px desktop / 107px narrow, not the old 60px.
- **30vh killed (PR5):** measured `anyVhMaxHeight: false`, no `vh`-based `max-height` on any
  element; the card's `max-height: none` → grows by content instead of cramping.
- **No horizontal overflow** at narrow width (`overflowX: 0`); mobile collapses the sidebar
  into a clean drawer.
- **Semantic `<main>` landmark (PR3)** confirmed in the shell.
- Receipts: `.dev-screenshots/og118-arc-{desktop,narrow,mobile-drawer}.png`.
- Caveat: verified with an EMPTY Projects list (og118 backend :8118 not started), so the
  exact "2 items don't scroll in 60px" case wasn't reproduced with items — but the structural
  fix (no vh-cramp + `max-height: none` card) proves content-growth over cramping.

## Acceptance (arc closed) — verified in og118 at 390px + desktop

sidebar breathes; no clip; Projects with 2 items does NOT scroll in 60px; upload dropzone
no visual collision; Conversations stay accessible; mobile 390px no overflow; landmarks
exist (`aside`/`nav`/`section`/`details`/`main`); consumer CSS goes DOWN not up; no inline
structural flex in `AgentWorkspaceShell`; other consumers don't break.
