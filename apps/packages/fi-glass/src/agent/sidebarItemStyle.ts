'use client';

/**
 * fi-glass · sidebar/resource item styles (B3-FIGLASS-SHELL-PRIMITIVES-1A).
 *
 * The og118 audit found `og-chat-item` and `og-project-item` were structural
 * twins — same flex row, `.is-active` tint, hover lift, and a destructive action
 * revealed on hover AND on coarse pointers — hand-written twice in the consumer.
 * Rather than each consumer (og118, slate, paper) re-authoring that skeleton, the
 * framework owns ONE injected stylesheet here, the same idempotent mechanism as
 * {@link ./../shell/touchTarget} (a `<style>` tag, present-once, SSR-safe).
 *
 * Everything is token-driven: the selected tint, hover, danger color and rename
 * input all read `--fi-sidebar-item-*` custom properties that fall back to the
 * `--glass-chat-*` theme tokens. A consumer re-tints by setting those vars on an
 * ancestor (og118 already does this via `body.glass-chat`) — no fi-glass edit and
 * no `og-*` class copied up. The coarse-pointer reveal is the one rule Tailwind
 * cannot express, which is exactly why it lives in an injected sheet.
 */

import { useEffect } from 'react';
import { ensureDensityStyle } from './densityStyle';

export const FI_SIDEBAR_ITEM_CLASS = 'fi-sidebar-item';
export const FI_ITEM_BODY_CLASS = 'fi-sidebar-item-body';
export const FI_ITEM_TITLE_CLASS = 'fi-sidebar-item-title';
export const FI_ITEM_SUBTITLE_CLASS = 'fi-sidebar-item-subtitle';
export const FI_ITEM_META_CLASS = 'fi-sidebar-item-meta';
export const FI_ITEM_ACTION_CLASS = 'fi-item-action';
export const FI_ITEM_ACTION_DANGER_CLASS = 'fi-item-action--danger';
export const FI_RESOURCE_RENAME_INPUT_CLASS = 'fi-resource-rename-input';

const SIDEBAR_ITEM_STYLE_ID = 'fi-sidebar-item-style';

const CSS = `
.${FI_SIDEBAR_ITEM_CLASS} {
  display: flex;
  align-items: flex-start;
  gap: var(--fi-item-gap, 0.4rem);
  padding: var(--fi-item-padding, 0.55rem 0.6rem);
  border-radius: 10px;
  border: 1px solid transparent;
  cursor: pointer;
  outline: none;
  transition: background 0.12s ease, border-color 0.12s ease;
}
.${FI_SIDEBAR_ITEM_CLASS}:hover {
  background: var(--fi-sidebar-item-hover-bg, rgba(255, 255, 255, 0.04));
}
.${FI_SIDEBAR_ITEM_CLASS}:focus-visible {
  box-shadow: 0 0 0 2px var(--glass-chat-accent-from, #059669);
}
.${FI_SIDEBAR_ITEM_CLASS}.is-selected {
  background: var(--fi-sidebar-item-selected-bg, rgba(52, 211, 153, 0.08));
  border-color: var(--fi-sidebar-item-selected-border, rgba(52, 211, 153, 0.3));
  cursor: default;
}
.${FI_SIDEBAR_ITEM_CLASS}.is-editing {
  cursor: default;
}
.${FI_ITEM_BODY_CLASS} {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
}
.${FI_ITEM_TITLE_CLASS} {
  font-size: 0.85rem;
  color: var(--glass-chat-text, #ffffff);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.${FI_ITEM_SUBTITLE_CLASS} {
  font-size: 0.75rem;
  color: var(--glass-chat-text-muted, #94a3b8);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.${FI_ITEM_META_CLASS} {
  font-size: 0.68rem;
  color: var(--fi-sidebar-item-meta-color, #475569);
}
.${FI_ITEM_ACTION_CLASS} {
  border: none;
  background: transparent;
  color: var(--fi-sidebar-item-action-color, #64748b);
  font-size: 1.1rem;
  line-height: 1;
  cursor: pointer;
  padding: 0 0.2rem;
  opacity: 0;
  transition: opacity 0.12s ease, color 0.12s ease;
}
.${FI_SIDEBAR_ITEM_CLASS}:hover .${FI_ITEM_ACTION_CLASS},
.${FI_ITEM_ACTION_CLASS}:focus-visible {
  opacity: 1;
}
.${FI_ITEM_ACTION_CLASS}:disabled {
  cursor: not-allowed;
  opacity: 0;
}
.${FI_ITEM_ACTION_DANGER_CLASS}:hover:not(:disabled) {
  color: var(--fi-sidebar-item-danger, #f87171);
}
@media (pointer: coarse) {
  .${FI_ITEM_ACTION_CLASS} {
    opacity: 1;
  }
  /* Touch has no hover to reveal actions, so they are always visible — but
     inline they steal the row's width (3 × 44px targets left a ~90px title on a
     390px phone). Wrap them to their own right-aligned line under the body
     instead: full-width readable title, intact 44px targets. */
  .${FI_SIDEBAR_ITEM_CLASS} {
    flex-wrap: wrap;
    justify-content: flex-end;
  }
  .${FI_ITEM_BODY_CLASS} {
    flex: 1 1 100%;
  }
}
@container fi-sidebar (max-width: 220px) {
  .${FI_SIDEBAR_ITEM_CLASS} {
    padding: var(--fi-item-padding-compact, 0.3rem 0.4rem);
    gap: var(--fi-item-gap-compact, 0.25rem);
  }
  .${FI_ITEM_META_CLASS} {
    display: none;
  }
}
.${FI_RESOURCE_RENAME_INPUT_CLASS} {
  font-size: 0.85rem;
  color: var(--glass-chat-text, #ffffff);
  background: var(--glass-chat-bg-mid, #0f172a);
  border: 1px solid var(--glass-chat-accent-from, #059669);
  border-radius: 4px;
  padding: 0.1rem 0.3rem;
  width: 100%;
  outline: none;
}
`;

/** Inject the idempotent sidebar-item stylesheet (no-op on the server / if already present). */
export function ensureSidebarItemStyle(): void {
  // The tokens this sheet READS are published by the density sheet; a primitive
  // never assumes an ancestor mounted it (same contract as touchTarget).
  ensureDensityStyle();

  if (typeof document === 'undefined') return;
  if (document.getElementById(SIDEBAR_ITEM_STYLE_ID)) return;
  const el = document.createElement('style');
  el.id = SIDEBAR_ITEM_STYLE_ID;
  el.textContent = CSS;
  document.head.appendChild(el);
}

/** Ensure the sidebar-item stylesheet is present for the lifetime of the component. */
export function useSidebarItemStyle(): void {
  useEffect(() => {
    ensureSidebarItemStyle();
  }, []);
}
