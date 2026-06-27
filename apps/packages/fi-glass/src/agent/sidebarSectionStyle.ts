'use client';

/**
 * fi-glass · sidebar/resource section styles (B3-FIGLASS-SHELL-PRIMITIVES-1C).
 *
 * The og118 audit found `og-sidebar-head` and `og-projects-head` were structural
 * twins — the same flex row (title left, "+ Nuevo" action right, space-between)
 * hand-written twice in the consumer, just as `og-chat-item`/`og-project-item`
 * were (now {@link ./sidebarItemStyle}). This is the section *header* anatomy
 * lifted into the framework: ONE injected stylesheet, the same idempotent
 * present-once SSR-safe `<style>` mechanism as the item primitive.
 *
 * Everything is token-driven so a consumer re-shapes without copying CSS up: the
 * header padding (`--fi-section-head-padding`), its separator border
 * (`--fi-section-head-border`), and the title size/color
 * (`--fi-section-title-*`) all carry defaults that match the "plain" section
 * (the projects head) and are overridden by setting the vars on an ancestor (the
 * conversation rail sets the taller padding + bottom border on `body`/`.og-sidebar`).
 */

import { useEffect } from 'react';

export const FI_SIDEBAR_SECTION_CLASS = 'fi-sidebar-section';
export const FI_SECTION_HEAD_CLASS = 'fi-sidebar-section-head';
export const FI_SECTION_TITLE_CLASS = 'fi-sidebar-section-title';

const SIDEBAR_SECTION_STYLE_ID = 'fi-sidebar-section-style';

const CSS = `
.${FI_SIDEBAR_SECTION_CLASS} {
  display: flex;
  flex-direction: column;
  min-height: 0;
}
.${FI_SECTION_HEAD_CLASS} {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  padding: var(--fi-section-head-padding, 0.8rem 0.85rem 0.5rem);
  border-bottom: var(--fi-section-head-border, none);
}
.${FI_SECTION_TITLE_CLASS} {
  font-weight: 600;
  letter-spacing: -0.01em;
  font-size: var(--fi-section-title-size, inherit);
  color: var(--fi-section-title-color, inherit);
}
`;

/** Inject the idempotent sidebar-section stylesheet (no-op on the server / if already present). */
export function ensureSidebarSectionStyle(): void {
  if (typeof document === 'undefined') return;
  if (document.getElementById(SIDEBAR_SECTION_STYLE_ID)) return;
  const el = document.createElement('style');
  el.id = SIDEBAR_SECTION_STYLE_ID;
  el.textContent = CSS;
  document.head.appendChild(el);
}

/** Ensure the sidebar-section stylesheet is present for the lifetime of the component. */
export function useSidebarSectionStyle(): void {
  useEffect(() => {
    ensureSidebarSectionStyle();
  }, []);
}
