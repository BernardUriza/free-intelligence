'use client';

/**
 * fi-glass · spacing scale + density contract (B3-FIGLASS-UX-TOKENS-1).
 *
 * Level 1 of the distribution-contracts arc (see backlog
 * `b3-figlass-ux-distribution.md`). Before extracting section-cards or
 * scroll-regions, the spacing must stop being magic numbers (`gap: .25rem`,
 * `padding: 0.55rem 0.6rem`) scattered across the consumer and the primitive
 * stylesheets. This injects ONE idempotent sheet — same present-once SSR-safe
 * mechanism as {@link ./sidebarItemStyle} / {@link ./sidebarSectionStyle} — that
 * defines:
 *
 *  1. A base `--fi-space-1..5` scale (+ `--fi-radius-section`, `--fi-touch-target`)
 *     on the workspace root, so primitives reference steps, not literals.
 *  2. A real `density` contract: `.fi-density-{compact,comfortable,spacious}` set
 *     the derived spacing tokens (`--fi-item-*`, `--fi-section-*`, `--fi-sidebar-gap`)
 *     the section/item primitives now read.
 *
 * `density` was already a prop on AgentWorkspaceShell emitting `.fi-density-*`, but
 * NO stylesheet consumed it — it was a dead class. This makes it functional.
 *
 * BACKWARD-COMPATIBLE BY CONSTRUCTION: the default density is `comfortable`, and the
 * `.fi-density-comfortable` block reproduces the primitives' previous hardcoded
 * values EXACTLY. So every existing consumer renders byte-identically; `compact`
 * (tighter) and `spacious` (airier) are the new opt-in steps.
 */

import { useEffect } from 'react';
import { FI_MOBILE_QUERY } from '../theme/breakpoints';

const DENSITY_STYLE_ID = 'fi-density-style';

const CSS = `
/* B3-FIGLASS-TOKEN-LAYER-1 — the BASE scale sits on :root, not on
 * .fi-agent-workspace. Scoping it to the workspace meant a primitive used
 * OUTSIDE the shell (a bare ComposerFrame, a standalone AgentSidebarSection)
 * saw no tokens at all, which is exactly why every consumer re-wrote the
 * comfortable value as a literal fallback — the same number in two places,
 * drifting apart on the first edit. The base scale is the PACKAGE's scale, so
 * it belongs at the root; only the DENSITY VARIANTS below stay scoped, because
 * those are a per-subtree choice. A consumer still overrides any token at a
 * deeper scope — :root is the floor, not a ceiling. */
:root {
  --fi-space-1: 0.25rem;
  --fi-space-2: 0.5rem;
  --fi-space-3: 0.75rem;
  --fi-space-4: 1rem;
  --fi-space-5: 1.5rem;
  --fi-radius-section: 12px;
  --fi-touch-target: 44px;
}
/* CONV-MOBILE-RECLAIM-1 — the conversation surface's own spacing tokens. The
 * transcript/composer regions read these (with their previous literals as
 * fallbacks), so on a phone the chrome tightens and content dominates; desktop
 * resolves to the exact former values. Consumers re-tune by setting the vars. */
@media ${FI_MOBILE_QUERY} {
  .fi-agent-workspace {
    --fi-transcript-pad: 0.75rem 0.75rem 0.5rem;
    --fi-transcript-gap: 0.5rem;
    --fi-composer-bar-pt: 0.5rem;
    --fi-composer-bar-px: 0.75rem;
    --fi-composer-bar-pb: 0.5rem;
  }
}
.fi-density-comfortable {
  --fi-section-gap: 0.5rem;
  --fi-sidebar-gap: 0.5rem;
  --fi-item-gap: 0.4rem;
  --fi-item-padding: 0.55rem 0.6rem;
  --fi-section-head-gap: 0.5rem;
  --fi-section-head-padding: 0.8rem 0.85rem 0.5rem;
}
.fi-density-compact {
  --fi-section-gap: 0.25rem;
  --fi-sidebar-gap: 0.25rem;
  --fi-item-gap: 0.3rem;
  --fi-item-padding: 0.4rem 0.5rem;
  --fi-section-head-gap: 0.4rem;
  --fi-section-head-padding: 0.6rem 0.7rem 0.35rem;
}
.fi-density-spacious {
  --fi-section-gap: 0.85rem;
  --fi-sidebar-gap: 0.85rem;
  --fi-item-gap: 0.55rem;
  --fi-item-padding: 0.75rem 0.85rem;
  --fi-section-head-gap: 0.65rem;
  --fi-section-head-padding: 1rem 1rem 0.65rem;
}
`;

/** Inject the idempotent density/spacing stylesheet (no-op on the server / if already present). */
export function ensureDensityStyle(): void {
  if (typeof document === 'undefined') return;
  if (document.getElementById(DENSITY_STYLE_ID)) return;
  const el = document.createElement('style');
  el.id = DENSITY_STYLE_ID;
  el.textContent = CSS;
  document.head.appendChild(el);
}

/** Ensure the density/spacing stylesheet is present for the lifetime of the component. */
export function useDensityStyle(): void {
  useEffect(() => {
    ensureDensityStyle();
  }, []);
}
