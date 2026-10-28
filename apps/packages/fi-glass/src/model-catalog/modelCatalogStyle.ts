'use client';

// One idempotent injected sheet, same mechanism as personaAdminStyle: no consumer Tailwind scan needed.
// A consumer re-tints by setting `--fi-mc-*` on an ancestor.
import { useInsertionEffect } from 'react';
import { FI_MOBILE_QUERY, FI_TOUCH_QUERY } from '../theme/breakpoints';
import { glassTokens } from '../theme/glass-tokens.generated';
import { ensureAdminKitStyle } from '../admin-kit/adminKitStyle';

export const FI_MODEL_CATALOG_ROOT_CLASS = 'fi-model-catalog';

const STYLE_ID = 'fi-model-catalog-style';
const ACCENT = `var(--fi-mc-accent, ${glassTokens.accent})`;
const CATALOG = `var(--fi-mc-catalog-accent, #a78bfa)`;
const FEATURED = `var(--fi-mc-featured, #fbbf24)`;
const TEXT = `var(--glass-chat-text, ${glassTokens.text})`;
const MUTED = `var(--glass-chat-text-muted, ${glassTokens.textMuted})`;
const DANGER = `var(--fi-mc-danger, ${glassTokens.danger})`;
const BORDER = `var(--fi-mc-border, ${glassTokens.surfaceBorder})`;
const FIELD_BG = `var(--fi-mc-field-bg, ${glassTokens.searchFill})`;
const SURFACE = glassTokens.surface;
const MONO = 'ui-monospace, SFMono-Regular, Menlo, monospace';
const LINE = (side: string) =>
  `border-${side}-width: 1px; border-${side}-style: solid; border-${side}-color: ${BORDER};`;

const CSS = `
.${FI_MODEL_CATALOG_ROOT_CLASS} { color: ${TEXT}; font-size: 0.875rem; --fi-admin-sheet-width: 36rem; --fi-admin-panel-width: 42rem; --fi-admin-accent: ${ACCENT}; --fi-admin-secondary: ${CATALOG}; }
.fi-mc-input {
  width: 100%; box-sizing: border-box; padding: 0.55rem 0.75rem; border-radius: 10px; font: inherit; font-size: 0.875rem;
  color: ${TEXT}; background: ${FIELD_BG}; border-width: 1px; border-style: solid; border-color: ${BORDER}; outline: none;
}
.fi-mc-input:focus-visible { border-color: ${ACCENT}; box-shadow: 0 0 0 1px ${ACCENT}; }
.fi-mc-input option { color: #0f172a; }
textarea.fi-mc-input { resize: vertical; line-height: 1.5; }
.fi-mc-mono { font-family: ${MONO}; }
.fi-mc-title { margin: 0; font-size: 1.125rem; font-weight: 600; color: ${TEXT}; display: flex; align-items: center; gap: 0.5rem; }
.fi-mc-subtitle { margin: 0.15rem 0 0; font-size: 0.8125rem; color: ${MUTED}; }
.fi-mc-actions { display: flex; align-items: center; gap: 0.35rem; flex-wrap: wrap; }
.fi-mc-stack { display: flex; flex-direction: column; gap: 1rem; }
.fi-mc-grid2 { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 1rem; }
.fi-mc-field { display: flex; flex-direction: column; gap: 0.35rem; min-width: 0; }
.fi-mc-label { font-size: 0.8125rem; font-weight: 500; color: ${MUTED}; }
.fi-mc-hint { margin: 0; font-size: 0.75rem; color: ${MUTED}; }
.fi-mc-check { display: inline-flex; align-items: center; gap: 0.5rem; cursor: pointer; color: ${MUTED}; min-height: 36px; }
.fi-mc-check input { width: 1.1rem; height: 1.1rem; accent-color: ${ACCENT}; margin: 0; }
.fi-mc-filters { display: flex; align-items: center; justify-content: space-between; gap: 1rem; flex-wrap: wrap; margin-bottom: 1.5rem; }
.fi-mc-filters .fi-mc-input { width: auto; min-width: 14rem; }
.fi-mc-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(min(100%, 19rem), 1fr)); gap: 1.25rem; }
.fi-mc-empty { display: flex; flex-direction: column; align-items: center; gap: 0.6rem; padding: 3rem 1rem; color: ${MUTED}; text-align: center; }
.fi-mc-empty h3 { margin: 0; font-size: 1.125rem; font-weight: 600; color: ${TEXT}; }
.fi-mc-empty p { margin: 0; max-width: 28rem; }
.fi-mc-card {
  display: flex; flex-direction: column; gap: 0.9rem; padding: 1.25rem; border-radius: 14px; cursor: pointer; min-width: 0;
  background: ${SURFACE}; border-width: 1px; border-style: solid; border-color: ${BORDER}; transition: border-color 0.12s ease;
}
.fi-mc-card:hover { border-color: color-mix(in srgb, ${ACCENT} 50%, transparent); }
.fi-mc-card[data-selected="true"] { border-color: ${ACCENT}; background: color-mix(in srgb, ${ACCENT} 8%, ${SURFACE}); }
.fi-mc-card[data-active="false"] { opacity: 0.65; }
.fi-mc-card:focus-visible { outline: none; box-shadow: 0 0 0 2px ${ACCENT}; }
.fi-mc-card-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 0.5rem; }
.fi-mc-card-id { display: flex; align-items: center; gap: 0.75rem; min-width: 0; }
.fi-mc-card-name { margin: 0; font-size: 1rem; font-weight: 700; color: ${TEXT}; overflow-wrap: anywhere; }
.fi-mc-badge { display: inline-flex; align-items: center; gap: 0.2rem; margin-left: 0.4rem; padding: 0.05rem 0.4rem; border-radius: 6px; font-size: 0.6875rem; font-weight: 500; vertical-align: middle; background: ${glassTokens.chipFill}; color: ${MUTED}; }
.fi-mc-badge[data-tone="installed"] { color: ${ACCENT}; background: color-mix(in srgb, ${ACCENT} 18%, transparent); }
.fi-mc-badge[data-tone="featured"] { color: ${FEATURED}; background: color-mix(in srgb, ${FEATURED} 18%, transparent); }
.fi-mc-clamp1, .fi-mc-clamp2 { margin: 0; display: -webkit-box; -webkit-box-orient: vertical; overflow: hidden; }
.fi-mc-clamp1 { -webkit-line-clamp: 1; }
.fi-mc-clamp2 { -webkit-line-clamp: 2; color: ${MUTED}; font-size: 0.8125rem; }
.fi-mc-stats { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0.5rem; margin: 0; }
.fi-mc-mini { padding: 0.5rem 0.625rem; border-radius: 8px; background: ${glassTokens.chipFill}; min-width: 0; }
.fi-mc-mini dt { font-size: 0.6875rem; color: ${MUTED}; }
.fi-mc-mini dd { margin: 0; display: flex; align-items: center; gap: 0.35rem; font-family: ${MONO}; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.fi-mc-card-foot { padding-top: 0.75rem; ${LINE('top')} font-size: 0.75rem; color: ${MUTED}; }
.fi-mc-logo { flex: 0 0 auto; display: inline-flex; padding: 0.45rem; border-radius: 10px; border-width: 1px; border-style: solid; color: var(--fi-mc-logo, ${MUTED}); border-color: color-mix(in srgb, var(--fi-mc-logo, ${MUTED}) 45%, transparent); background: color-mix(in srgb, var(--fi-mc-logo, ${MUTED}) 14%, transparent); }
.fi-mc-logo[data-provider="openai"], .fi-mc-logo[data-provider="gpt4all"] { --fi-mc-logo: #34d399; }
.fi-mc-logo[data-provider="anthropic"] { --fi-mc-logo: #fb923c; }
.fi-mc-logo[data-provider="azure"] { --fi-mc-logo: #60a5fa; }
.fi-mc-logo[data-provider="ollama"] { --fi-mc-logo: #c084fc; }
.fi-mc-logo[data-provider="huggingface"] { --fi-mc-logo: #facc15; }
.fi-mc-panel { margin-bottom: 1.5rem; padding: 1.25rem; border-radius: 14px; background: ${SURFACE}; border-width: 1px; border-style: solid; border-color: ${BORDER}; }
.fi-mc-panel-head { display: flex; align-items: center; justify-content: space-between; gap: 0.75rem; margin-bottom: 1rem; }
.fi-mc-row-between { display: flex; align-items: center; justify-content: space-between; gap: 0.5rem; flex-wrap: wrap; }
.fi-mc-inline { display: inline-flex; align-items: center; gap: 0.4rem; min-width: 0; }
.fi-mc-muted { color: ${MUTED}; }
.fi-mc-small { font-size: 0.75rem; color: ${MUTED}; }
.fi-mc-meter { height: 0.6rem; margin: 0.5rem 0 0.3rem; border-radius: 999px; overflow: hidden; background: ${glassTokens.chipFill}; }
.fi-mc-meter > div { height: 100%; border-radius: inherit; transition: width 0.3s ease; background: ${ACCENT}; }
.fi-mc-meter[data-level="warn"] > div { background: #facc15; }
.fi-mc-meter[data-level="danger"] > div { background: #fb923c; }
.fi-mc-meter[data-level="critical"] > div { background: ${DANGER}; }
.fi-mc-meter[data-tone="catalog"] { height: 0.4rem; margin: 0.5rem 0 0.2rem; }
.fi-mc-meter[data-tone="catalog"] > div { background: ${CATALOG}; }
.fi-mc-section { margin-top: 1rem; padding-top: 1rem; ${LINE('top')} }
.fi-mc-running { display: flex; flex-direction: column; gap: 0.5rem; margin-top: 0.75rem; }
.fi-mc-running-item { display: flex; align-items: center; justify-content: space-between; gap: 0.5rem; padding: 0.5rem 0.75rem; border-radius: 10px; background: ${glassTokens.chipFill}; }
.fi-mc-proc { padding: 0.05rem 0.4rem; border-radius: 6px; font-size: 0.6875rem; font-weight: 600; font-family: ${MONO}; color: ${MUTED}; background: ${glassTokens.chipFill}; }
.fi-mc-proc[data-processor="gpu"] { color: ${ACCENT}; background: color-mix(in srgb, ${ACCENT} 18%, transparent); }
.fi-mc-proc[data-processor="partial"] { color: #facc15; background: rgba(250, 204, 21, 0.15); }
.fi-mc-dot { display: inline-block; width: 0.5rem; height: 0.5rem; border-radius: 999px; background: ${ACCENT}; }
.fi-mc-sources { display: flex; flex-wrap: wrap; gap: 0.5rem; margin: 0.75rem 0; }
.fi-mc-chip { display: inline-flex; align-items: center; gap: 0.35rem; padding: 0.3rem 0.7rem; border-radius: 999px; font-size: 0.75rem; color: ${MUTED}; background: ${glassTokens.chipFill}; border-width: 1px; border-style: solid; border-color: ${BORDER}; }
.fi-mc-chip[data-status="loading"] { color: #60a5fa; }
.fi-mc-chip[data-status="loaded"] { color: ${ACCENT}; }
.fi-mc-chip[data-status="error"] { color: ${DANGER}; }
.fi-mc-toolbar { display: flex; gap: 0.5rem; align-items: center; }
.fi-mc-search { position: relative; flex: 1 1 auto; min-width: 0; }
.fi-mc-search svg { position: absolute; left: 0.75rem; top: 50%; transform: translateY(-50%); color: ${MUTED}; pointer-events: none; }
.fi-mc-search .fi-mc-input { padding-left: 2.25rem; }
.fi-mc-toolbar select.fi-mc-input { width: 7.5rem; flex: 0 0 auto; }
.fi-mc-tabs { display: flex; gap: 0.35rem; overflow-x: auto; margin-top: 0.75rem; padding-bottom: 0.15rem; scrollbar-width: none; }
.fi-mc-tab[aria-selected="true"] { color: #fff; background: color-mix(in srgb, ${CATALOG} 70%, transparent); border-color: transparent; }
.fi-mc-count { padding: 0 0.35rem; border-radius: 6px; font-size: 0.6875rem; background: rgba(0, 0, 0, 0.25); }
.fi-mc-section-title { display: flex; align-items: center; gap: 0.4rem; margin: 0 0 0.6rem; font-size: 0.75rem; font-weight: 600; letter-spacing: 0.04em; color: ${MUTED}; }
.fi-mc-section-title[data-tone="featured"] { color: ${FEATURED}; }
.fi-mc-list { display: flex; flex-direction: column; gap: 0.4rem; margin: 0 0 1.25rem; padding: 0; list-style: none; }
.fi-mc-row {
  display: flex; align-items: center; gap: 0.75rem; padding: 0.75rem; border-radius: 12px; min-width: 0;
  background: ${glassTokens.chipFill}; border-width: 1px; border-style: solid; border-color: ${BORDER};
}
.fi-mc-row[data-installed="true"] { border-color: color-mix(in srgb, ${ACCENT} 35%, transparent); }
.fi-mc-row[data-featured="true"] { border-color: color-mix(in srgb, ${FEATURED} 35%, transparent); }
.fi-mc-row[data-selected="true"] { box-shadow: 0 0 0 2px ${CATALOG}; }
.fi-mc-row-info { flex: 1 1 auto; min-width: 0; }
.fi-mc-row-name { font-weight: 500; color: ${TEXT}; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.fi-mc-row-meta { display: flex; flex-wrap: wrap; gap: 0.25rem 0.75rem; margin-top: 0.15rem; font-size: 0.75rem; color: ${MUTED}; }
.fi-mc-row-error { margin: 0.25rem 0 0; font-size: 0.75rem; color: ${DANGER}; }
.fi-mc-skel { height: 3.75rem; border-radius: 12px; background: linear-gradient(90deg, ${glassTokens.chipFill} 25%, rgba(255, 255, 255, 0.09) 50%, ${glassTokens.chipFill} 75%); background-size: 200% 100%; animation: fi-mc-shimmer 1.4s ease-in-out infinite; }
@keyframes fi-mc-shimmer { from { background-position: 200% 0; } to { background-position: -200% 0; } }
.fi-mc-keys { display: flex; justify-content: space-between; gap: 1rem; font-size: 0.75rem; color: ${MUTED}; }
.fi-mc-result { display: flex; flex-direction: column; gap: 0.35rem; padding: 0.75rem 1rem; border-radius: 10px; background: ${glassTokens.chipFill}; }
.fi-mc-result[data-tone="success"] { background: color-mix(in srgb, ${ACCENT} 10%, transparent); border: 1px solid color-mix(in srgb, ${ACCENT} 35%, transparent); }
.fi-mc-result[data-tone="error"] { background: rgba(248, 113, 113, 0.08); border: 1px solid rgba(248, 113, 113, 0.35); }
.fi-mc-result p { margin: 0; white-space: pre-wrap; overflow-wrap: anywhere; }
.fi-mc-result .fi-mc-label { text-transform: uppercase; font-size: 0.6875rem; letter-spacing: 0.05em; }
@media ${FI_MOBILE_QUERY} {
  .fi-mc-grid2, .fi-mc-stats { grid-template-columns: minmax(0, 1fr); }
  .fi-mc-input { font-size: 16px; }
  .fi-mc-filters .fi-mc-input { min-width: 0; flex: 1 1 auto; }
  .fi-mc-toolbar { flex-wrap: wrap; }
  .fi-mc-search { flex-basis: 100%; }
  .fi-mc-toolbar select.fi-mc-input { flex: 1 1 auto; width: auto; }
  .fi-mc-panel { padding: 1rem 0.75rem; }
}
@media ${FI_TOUCH_QUERY} {
  .fi-mc-input, .fi-mc-check { min-height: var(--fi-touch-target, 44px); }
  .fi-mc-keys { display: none; }
}
`;

/** Inject the idempotent model-catalog stylesheet (no-op on the server / if already present). */
export function ensureModelCatalogStyle(): void {
  if (typeof document === 'undefined') return;
  ensureAdminKitStyle();
  if (document.getElementById(STYLE_ID)) return;
  const el = document.createElement('style');
  el.id = STYLE_ID;
  el.textContent = CSS;
  document.head.appendChild(el);
}

export function useModelCatalogStyle(): void {
  useInsertionEffect(() => {
    ensureModelCatalogStyle();
  }, []);
}
