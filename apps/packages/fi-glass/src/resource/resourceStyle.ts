'use client';

/**
 * fi-glass · resource-workspace styles (FIGLASS-PROJECTS-PAGE-1, capa fi-glass).
 *
 * The anatomy of a "resource" seen as a PAGE rather than a sidebar row: an index
 * of cards, and a detail split into a main column plus a rail of panels. og118
 * renders projects with it; fi-glass does not know that word, and nothing here
 * may learn it.
 *
 * Same mechanism as {@link ../agent/sidebarItemStyle} and
 * {@link ../shell/touchTarget}: ONE idempotent injected `<style>`, SSR-safe,
 * every literal interpolated from the token contract instead of typed by hand —
 * the drift that `glass-tokens.generated` exists to stop.
 *
 * A consumer re-tints by setting `--fi-resource-*` on an ancestor. It never
 * copies a class up, and it never edits this file.
 */

import { useEffect } from 'react';
import { FI_MOBILE_QUERY, FI_TOUCH_QUERY } from '../theme/breakpoints';
import { glassTokens } from '../theme/glass-tokens.generated';

export const FI_INDEX_HEADER_CLASS = 'fi-resource-index-header';
export const FI_INDEX_TITLE_CLASS = 'fi-resource-index-title';
export const FI_INDEX_ACTIONS_CLASS = 'fi-resource-index-actions';
export const FI_SEARCH_CLASS = 'fi-resource-search';
export const FI_CARD_GRID_CLASS = 'fi-resource-card-grid';
export const FI_CARD_CLASS = 'fi-resource-card';
export const FI_CARD_TITLE_CLASS = 'fi-resource-card-title';
export const FI_CARD_DESC_CLASS = 'fi-resource-card-desc';
export const FI_CARD_META_CLASS = 'fi-resource-card-meta';
export const FI_DETAIL_CLASS = 'fi-workspace-detail';
export const FI_DETAIL_MAIN_CLASS = 'fi-workspace-main';
export const FI_DETAIL_RAIL_CLASS = 'fi-workspace-rail';
export const FI_RAIL_STACK_CLASS = 'fi-rail-stack';
export const FI_RAIL_PANEL_CLASS = 'fi-rail-panel';
export const FI_RAIL_PANEL_HEAD_CLASS = 'fi-rail-panel-head';
export const FI_RAIL_PANEL_TITLE_CLASS = 'fi-rail-panel-title';
export const FI_METER_CLASS = 'fi-capacity-meter';
export const FI_METER_TRACK_CLASS = 'fi-capacity-meter-track';
export const FI_METER_FILL_CLASS = 'fi-capacity-meter-fill';
export const FI_METER_LABEL_CLASS = 'fi-capacity-meter-label';
export const FI_DOC_GRID_CLASS = 'fi-doc-grid';
export const FI_DOC_CARD_CLASS = 'fi-doc-card';
export const FI_DOC_CARD_TITLE_CLASS = 'fi-doc-card-title';
export const FI_DOC_CARD_META_CLASS = 'fi-doc-card-meta';
export const FI_DOC_CARD_BADGE_CLASS = 'fi-doc-card-badge';
export const FI_BREADCRUMB_CLASS = 'fi-workspace-breadcrumb';

const RESOURCE_STYLE_ID = 'fi-resource-style';

/* The detail rail is 352px and the index tops out at 896px — both measured on
   the live surface this anatomy was copied from, both overridable as tokens so a
   consumer with a different shell is not stuck with someone else's column. */
const CSS = `
.${FI_INDEX_HEADER_CLASS} {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  flex-wrap: wrap;
}
.${FI_INDEX_TITLE_CLASS} {
  font-size: var(--fi-resource-title-size, 1.5rem);
  font-weight: 500;
  color: var(--glass-chat-text, ${glassTokens.text});
  margin: 0;
}
.${FI_INDEX_ACTIONS_CLASS} {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.${FI_SEARCH_CLASS} {
  width: 100%;
  box-sizing: border-box;
  height: var(--fi-resource-search-height, 40px);
  border-radius: 10px;
  padding: 0 0.75rem;
  color: var(--glass-chat-text, ${glassTokens.text});
  background: var(--fi-resource-search-fill, ${glassTokens.searchFill});
  border: 1px solid var(--fi-resource-search-border, ${glassTokens.searchBorder});
  outline: none;
}
.${FI_SEARCH_CLASS}:focus-visible {
  box-shadow: 0 0 0 2px var(--glass-chat-accent-from, ${glassTokens.accentDeep});
}
.${FI_CARD_GRID_CLASS} {
  display: grid;
  grid-template-columns: 1fr;
  gap: 0.75rem;
  grid-auto-rows: 1fr;
  list-style: none;
  margin: 0;
  padding: 0;
}
@media not all and ${FI_MOBILE_QUERY} {
  .${FI_CARD_GRID_CLASS} {
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 1.5rem;
  }
}
.${FI_CARD_CLASS} {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding: 1rem;
  height: 100%;
  box-sizing: border-box;
  border-radius: 12px;
  text-align: left;
  cursor: pointer;
  border: 1px solid var(--fi-resource-card-border, ${glassTokens.surfaceBorder});
  background: var(--fi-resource-card-bg, ${glassTokens.surface});
  color: inherit;
  text-decoration: none;
  transition: background 0.12s ease, transform 0.12s ease;
}
.${FI_CARD_CLASS}:hover {
  background: var(--fi-resource-card-hover-bg, ${glassTokens.itemHover});
}
.${FI_CARD_CLASS}:active {
  transform: scale(0.98);
}
.${FI_CARD_CLASS}:focus-visible {
  outline: none;
  box-shadow: 0 0 0 2px var(--glass-chat-accent-from, ${glassTokens.accentDeep});
}
.${FI_CARD_TITLE_CLASS} {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--glass-chat-text, ${glassTokens.text});
}
.${FI_CARD_DESC_CLASS} {
  font-size: 0.875rem;
  color: var(--glass-chat-text-muted, ${glassTokens.textMuted});
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.${FI_CARD_META_CLASS} {
  margin-top: auto;
  font-size: 0.8125rem;
  color: var(--fi-resource-card-meta-color, ${glassTokens.itemMeta});
}
.${FI_DETAIL_CLASS} {
  display: flex;
  align-items: flex-start;
  gap: 1.5rem;
}
.${FI_DETAIL_MAIN_CLASS} {
  flex: 1 1 auto;
  min-width: 0;
}
.${FI_DETAIL_RAIL_CLASS} {
  flex: 0 0 var(--fi-resource-rail-width, 352px);
  width: var(--fi-resource-rail-width, 352px);
  max-width: 100%;
}
@media ${FI_MOBILE_QUERY} {
  /* The rail stacks UNDER the main column — it never becomes a 352px sliver
     beside a crushed conversation. */
  .${FI_DETAIL_CLASS} {
    flex-direction: column;
    gap: 1rem;
  }
  .${FI_DETAIL_RAIL_CLASS} {
    flex: 1 1 auto;
    width: 100%;
  }
}
.${FI_RAIL_STACK_CLASS} {
  display: flex;
  flex-direction: column;
  border: 0.5px solid var(--fi-resource-rail-border, ${glassTokens.surfaceBorder});
  border-radius: 16px;
  overflow: hidden;
}
.${FI_RAIL_PANEL_CLASS} {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
}
.${FI_RAIL_PANEL_CLASS} + .${FI_RAIL_PANEL_CLASS} {
  border-top: 1px solid var(--fi-resource-rail-divider, ${glassTokens.sidebarDivider});
}
.${FI_RAIL_PANEL_HEAD_CLASS} {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}
.${FI_RAIL_PANEL_TITLE_CLASS} {
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--glass-chat-text, ${glassTokens.text});
}
.${FI_METER_CLASS} {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}
.${FI_METER_TRACK_CLASS} {
  height: 4px;
  border-radius: 2px;
  overflow: hidden;
  background: var(--fi-resource-meter-track, ${glassTokens.chipFill});
}
.${FI_METER_FILL_CLASS} {
  height: 100%;
  border-radius: 2px;
  background: var(--fi-resource-meter-fill, ${glassTokens.accent});
  transition: width 0.2s ease;
}
.${FI_METER_LABEL_CLASS} {
  font-size: 0.75rem;
  color: var(--glass-chat-text-muted, ${glassTokens.textMuted});
}
.${FI_DOC_GRID_CLASS} {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.5rem;
  list-style: none;
  margin: 0;
  padding: 0;
}
.${FI_DOC_CARD_CLASS} {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  min-height: var(--fi-resource-doc-card-height, 120px);
  padding: 0.6rem;
  box-sizing: border-box;
  border-radius: 10px;
  text-align: left;
  border: 1px solid var(--fi-resource-card-border, ${glassTokens.surfaceBorder});
  background: var(--fi-resource-card-bg, ${glassTokens.surface});
  color: inherit;
  cursor: pointer;
}
.${FI_DOC_CARD_CLASS}:hover {
  background: var(--fi-resource-card-hover-bg, ${glassTokens.itemHover});
}
.${FI_DOC_CARD_TITLE_CLASS} {
  font-size: 0.8125rem;
  color: var(--glass-chat-text, ${glassTokens.text});
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  word-break: break-word;
}
.${FI_DOC_CARD_META_CLASS} {
  margin-top: auto;
  font-size: 0.75rem;
  color: var(--fi-resource-card-meta-color, ${glassTokens.itemMeta});
}
.${FI_DOC_CARD_BADGE_CLASS} {
  align-self: flex-start;
  font-size: 0.6875rem;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  padding: 0.1rem 0.35rem;
  border-radius: 4px;
  border: 1px solid var(--fi-resource-badge-border, ${glassTokens.chipBorder});
  color: var(--glass-chat-text-muted, ${glassTokens.textMuted});
}
@media ${FI_TOUCH_QUERY} {
  /* Measured at a phone viewport and caught below the minimum: the search box
     shipped at the 40px it was copied from, and 40 is not 44. A control the
     thumb has to hit is a touch target no matter how elegant the spec was. */
  .${FI_SEARCH_CLASS} {
    height: auto;
    min-height: var(--fi-touch-target, 44px);
  }
}
.${FI_BREADCRUMB_CLASS} {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.35rem;
  font-size: 0.8125rem;
  color: var(--glass-chat-text-muted, ${glassTokens.textMuted});
}
.${FI_BREADCRUMB_CLASS} a,
.${FI_BREADCRUMB_CLASS} button {
  color: inherit;
  background: none;
  border: none;
  padding: 0;
  font: inherit;
  cursor: pointer;
  text-decoration: none;
}
.${FI_BREADCRUMB_CLASS} a:hover,
.${FI_BREADCRUMB_CLASS} button:hover {
  color: var(--glass-chat-text, ${glassTokens.text});
}
`;

/** Inject the idempotent resource-workspace stylesheet (no-op on the server / if already present). */
export function ensureResourceStyle(): void {
  if (typeof document === 'undefined') return;
  if (document.getElementById(RESOURCE_STYLE_ID)) return;
  const el = document.createElement('style');
  el.id = RESOURCE_STYLE_ID;
  el.textContent = CSS;
  document.head.appendChild(el);
}

/** Ensure the resource-workspace stylesheet is present for the lifetime of the component. */
export function useResourceStyle(): void {
  useEffect(() => {
    ensureResourceStyle();
  }, []);
}
