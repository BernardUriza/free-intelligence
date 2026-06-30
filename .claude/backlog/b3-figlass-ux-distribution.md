# B3-FIGLASS-UX-DISTRIBUTION-1 — distribution contracts for fi-glass (spacing/semantic/cards/scroll/CQ)

Status: Proposed
Proposed: 2026-06-30 by Bernard (UX feedback on og118 sidebar) + coagent plan

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

1. **B3-FIGLASS-UX-DISTRIBUTION-AUDIT-1** — read-only smell matrix (✅ above).
2. **B3-FIGLASS-UX-TOKENS-1** — spacing scale (`--fi-space-1..5`, `--fi-section-padding`,
   `--fi-section-gap`, `--fi-touch-target`) + `density` contract. Conservative defaults
   (current look ≈ `compact`; og118 opts into `comfortable` for air). Small, low risk.
3. **B3-FIGLASS-SEMANTIC-SHELL-1** — replace inline-flex slots with `main`/`aside`/`nav`/
   `section`/`header` landmarks + aria-labels. Visual-equivalent, no consumer CSS to
   survive, no mobile regression.
4. **B3-FIGLASS-SIDEBAR-SECTIONS-2** — extend `AgentSidebarSection`: `variant="plain"|"card"`,
   `collapsible`/`defaultCollapsed` (`<details>/<summary>`), header/action/footer slots,
   `emptyState`, `scrollBehavior`. og118 Projects → `variant="card"`.
5. **B3-FIGLASS-SCROLL-REGIONS-1** — `AgentScrollRegion` (or section-integrated):
   `maxItemsBeforeScroll`, content-aware `max-block-size`. **Kills `max-height:30vh`** —
   Projects grows by content (1–3 items, no premature scroll), dropzone gets real gap,
   Conversations keep filling remaining space without being crushed.
6. **B3-FIGLASS-CONTAINER-QUERIES-1** — `container-type:inline-size` per panel; narrow
   sidebar = compact rows, wide = show meta; narrow composer = icon-only labels. Last,
   because CQ without the semantic primitives just masks old CSS.

## The decision that's the owner's

How deep to take the arc, and when. PR1 (audit) is done. PRs 2→6 are real framework
changes touching the shared shell — each is greenlit per-level by Bernard. Recommended
entry after audit: PR2 (tokens) — small and unblocks 4/5.

## Acceptance (arc closed) — verified in og118 at 390px + desktop

sidebar breathes; no clip; Projects with 2 items does NOT scroll in 60px; upload dropzone
no visual collision; Conversations stay accessible; mobile 390px no overflow; landmarks
exist (`aside`/`nav`/`section`/`details`/`main`); consumer CSS goes DOWN not up; no inline
structural flex in `AgentWorkspaceShell`; other consumers don't break.
