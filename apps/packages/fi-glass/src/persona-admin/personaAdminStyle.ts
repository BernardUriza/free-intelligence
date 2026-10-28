'use client';

// One idempotent injected sheet, same mechanism as resourceStyle: no consumer Tailwind scan needed.
// A consumer re-tints by setting `--fi-persona-*` on an ancestor.
import { useInsertionEffect } from 'react';
import { FI_MOBILE_QUERY, FI_TOUCH_QUERY } from '../theme/breakpoints';
import { glassTokens } from '../theme/glass-tokens.generated';
import { ensureTouchTargetStyle } from '../shell/touchTarget';

export const FI_PERSONA_ROOT_CLASS = 'fi-persona-admin';

const STYLE_ID = 'fi-persona-admin-style';
const ACCENT = `var(--fi-persona-accent, ${glassTokens.accent})`;
const TEXT = `var(--glass-chat-text, ${glassTokens.text})`;
const MUTED = `var(--glass-chat-text-muted, ${glassTokens.textMuted})`;
const DANGER = `var(--fi-persona-danger, ${glassTokens.danger})`;
const BORDER = `var(--fi-persona-border, ${glassTokens.surfaceBorder})`;
const FIELD_BG = `var(--fi-persona-field-bg, ${glassTokens.searchFill})`;
const PANEL_BG = `var(--fi-persona-panel-bg, ${glassTokens.bgMid})`;

const CSS = `
.${FI_PERSONA_ROOT_CLASS} { color: ${TEXT}; font-size: 0.875rem; }
.fi-persona-stack { display: flex; flex-direction: column; gap: 1.25rem; }
.fi-persona-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 1rem; }
.fi-persona-field { display: flex; flex-direction: column; gap: 0.35rem; min-width: 0; }
.fi-persona-label { display: flex; align-items: center; gap: 0.4rem; font-size: 0.8125rem; font-weight: 500; color: ${MUTED}; }
.fi-persona-required { color: ${DANGER}; }
.fi-persona-input {
  width: 100%; box-sizing: border-box; padding: 0.625rem 0.75rem; border-radius: 10px;
  font: inherit; font-size: 0.875rem; color: ${TEXT}; background: ${FIELD_BG};
  border-width: 1px; border-style: solid; border-color: ${BORDER}; outline: none; transition: border-color 0.12s ease;
}
.fi-persona-input:focus-visible { border-color: ${ACCENT}; box-shadow: 0 0 0 1px ${ACCENT}; }
.fi-persona-input[aria-invalid="true"] { border-color: ${DANGER}; }
.fi-persona-input:disabled { opacity: 0.55; cursor: not-allowed; }
.fi-persona-input option, .fi-persona-input optgroup { color: #0f172a; }
textarea.fi-persona-input { resize: vertical; line-height: 1.5; }
.fi-persona-mono { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
.fi-persona-range { width: 100%; accent-color: ${ACCENT}; min-height: 24px; }
.fi-persona-hint { display: flex; justify-content: space-between; gap: 0.5rem; font-size: 0.75rem; color: ${MUTED}; }
.fi-persona-error { display: flex; align-items: center; gap: 0.25rem; margin: 0; font-size: 0.75rem; color: ${DANGER}; }
.fi-persona-alert {
  display: flex; align-items: flex-start; gap: 0.5rem; margin: 0; padding: 0.75rem; border-radius: 10px;
  color: ${DANGER}; background: rgba(248, 113, 113, 0.08); border-width: 1px; border-style: solid; border-color: rgba(248, 113, 113, 0.35);
}
.fi-persona-btn {
  display: inline-flex; align-items: center; justify-content: center; gap: 0.4rem; min-height: 36px;
  padding: 0.5rem 0.9rem; border-radius: 10px; font: inherit; font-size: 0.875rem; font-weight: 500;
  cursor: pointer; color: ${TEXT}; background: ${FIELD_BG}; border-width: 1px; border-style: solid; border-color: ${BORDER};
}
.fi-persona-btn:disabled { opacity: 0.55; cursor: not-allowed; }
.fi-persona-btn:focus-visible { outline: none; box-shadow: 0 0 0 2px ${ACCENT}; }
.fi-persona-btn[data-variant="primary"] { color: #04130d; background: ${ACCENT}; border-color: transparent; }
.fi-persona-btn[data-variant="ghost"] { background: transparent; border-color: transparent; }
.fi-persona-btn[data-variant="ghost"]:hover { background: ${glassTokens.itemHover}; }
.fi-persona-btn[data-variant="danger"] { color: ${DANGER}; background: transparent; border-color: rgba(248, 113, 113, 0.35); }
.fi-persona-btn[data-icon-only] { padding: 0.4rem; min-width: 36px; }
.fi-persona-spin { animation: fi-persona-spin 1s linear infinite; }
@keyframes fi-persona-spin { to { transform: rotate(360deg); } }
.fi-persona-overlay { position: fixed; inset: 0; z-index: 50; display: flex; }
.fi-persona-backdrop { position: absolute; inset: 0; background: rgba(0, 0, 0, 0.6); backdrop-filter: blur(4px); }
.fi-persona-sheet {
  position: relative; display: flex; flex-direction: column; margin: auto; width: 100%;
  max-width: var(--fi-persona-sheet-width, 42rem); max-height: calc(100dvh - 2rem);
  background: ${PANEL_BG}; border-width: 1px; border-style: solid; border-color: ${BORDER}; border-radius: 16px; overflow: hidden;
  box-shadow: 0 24px 48px rgba(0, 0, 0, 0.45);
}
.fi-persona-overlay[data-placement="side"] .fi-persona-sheet {
  margin: 0 0 0 auto; height: 100dvh; max-height: none; max-width: var(--fi-persona-panel-width, 64rem);
  border-radius: 0; border: 0; border-left-width: 1px; border-left-style: solid; border-left-color: ${BORDER};
}
.fi-persona-sheet-head, .fi-persona-sheet-foot {
  flex: 0 0 auto; display: flex; align-items: center; justify-content: space-between; gap: 0.75rem;
  padding: 1rem 1.5rem; flex-wrap: wrap;
}
.fi-persona-sheet-head { border-bottom-width: 1px; border-bottom-style: solid; border-bottom-color: ${BORDER}; }
.fi-persona-sheet-foot { border-top-width: 1px; border-top-style: solid; border-top-color: ${BORDER}; }
.fi-persona-sheet-body { flex: 1 1 auto; overflow-y: auto; padding: 1.25rem 1.5rem; }
.fi-persona-title { margin: 0; font-size: 1.125rem; font-weight: 600; color: ${TEXT}; display: flex; align-items: center; gap: 0.5rem; }
.fi-persona-subtitle { margin: 0.15rem 0 0; font-size: 0.8125rem; color: ${MUTED}; }
.fi-persona-actions { display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; }
.fi-persona-tabs { display: flex; gap: 0.35rem; overflow-x: auto; width: 100%; scrollbar-width: none; }
.fi-persona-tab { white-space: nowrap; }
.fi-persona-tab[aria-selected="true"] { border-color: ${ACCENT}; color: ${ACCENT}; }
.fi-persona-card {
  display: flex; flex-direction: column; gap: 1rem; padding: 1.25rem; border-radius: 14px; cursor: pointer;
  text-align: left; color: inherit; background: ${glassTokens.surface};
  border-width: 1px; border-style: solid; border-color: color-mix(in srgb, ${ACCENT} 30%, transparent); transition: border-color 0.12s ease, background 0.12s ease;
}
.fi-persona-card:hover { border-color: ${ACCENT}; }
.fi-persona-card[data-selected="true"] { border-color: ${ACCENT}; background: color-mix(in srgb, ${ACCENT} 10%, ${glassTokens.surface}); }
.fi-persona-card:focus-visible { outline: none; box-shadow: 0 0 0 2px ${ACCENT}; }
.fi-persona-card-head { display: flex; align-items: center; justify-content: space-between; gap: 0.75rem; }
.fi-persona-card-id { display: flex; align-items: center; gap: 0.75rem; min-width: 0; }
.fi-persona-card-icon {
  flex: 0 0 auto; display: inline-flex; padding: 0.5rem; border-radius: 10px; color: ${ACCENT};
  background: color-mix(in srgb, ${ACCENT} 15%, transparent); border-width: 1px; border-style: solid; border-color: color-mix(in srgb, ${ACCENT} 40%, transparent);
}
.fi-persona-card-name { margin: 0; font-size: 1.0625rem; font-weight: 700; color: ${TEXT}; overflow: hidden; text-overflow: ellipsis; }
.fi-persona-card-desc {
  margin: 0; color: ${MUTED}; min-height: 2.5em; display: -webkit-box; -webkit-line-clamp: 2;
  -webkit-box-orient: vertical; overflow: hidden;
}
.fi-persona-card-stats { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0.5rem; }
.fi-persona-mini { padding: 0.5rem 0.625rem; border-radius: 8px; background: ${glassTokens.chipFill}; min-width: 0; }
.fi-persona-mini dt { font-size: 0.6875rem; color: ${MUTED}; }
.fi-persona-mini dd { margin: 0; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.fi-persona-card-foot { display: flex; flex-direction: column; gap: 0.25rem; padding-top: 0.75rem; border-top-width: 1px; border-top-style: solid; border-top-color: ${BORDER}; font-size: 0.75rem; color: ${MUTED}; }
.fi-persona-row { display: flex; justify-content: space-between; gap: 0.5rem; }
.fi-persona-row b { color: ${TEXT}; font-weight: 600; }
.fi-persona-example { display: flex; flex-direction: column; gap: 0.75rem; padding: 1rem; border-radius: 12px; background: ${glassTokens.surface}; border-width: 1px; border-style: solid; border-color: ${BORDER}; }
.fi-persona-pre { margin: 0; padding: 1rem; border-radius: 10px; white-space: pre-wrap; overflow-x: auto; background: ${glassTokens.codeBlockBg}; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 0.8125rem; }
.fi-persona-empty { display: flex; flex-direction: column; align-items: center; gap: 0.5rem; padding: 2rem 1rem; color: ${MUTED}; text-align: center; }
@media ${FI_MOBILE_QUERY} {
  .fi-persona-grid, .fi-persona-card-stats { grid-template-columns: minmax(0, 1fr); }
  .fi-persona-input { font-size: 16px; }
  .fi-persona-sheet, .fi-persona-overlay[data-placement="side"] .fi-persona-sheet {
    margin: 0; max-width: none; max-height: none; height: 100dvh; border-radius: 0; border: 0;
  }
  .fi-persona-sheet-head { padding: calc(0.75rem + env(safe-area-inset-top)) 0.75rem 0.75rem; }
  .fi-persona-sheet-body { padding: 1rem 0.75rem; }
  .fi-persona-sheet-foot { padding: 0.75rem 0.75rem calc(0.75rem + env(safe-area-inset-bottom)); }
}
@media ${FI_TOUCH_QUERY} {
  .fi-persona-input, .fi-persona-btn { min-height: var(--fi-touch-target, 44px); }
  .fi-persona-btn[data-icon-only] { min-width: var(--fi-touch-target, 44px); }
}
`;

/** Inject the idempotent persona-admin stylesheet (no-op on the server / if already present). */
export function ensurePersonaAdminStyle(): void {
  if (typeof document === 'undefined') return;
  ensureTouchTargetStyle();
  if (document.getElementById(STYLE_ID)) return;
  const el = document.createElement('style');
  el.id = STYLE_ID;
  el.textContent = CSS;
  document.head.appendChild(el);
}

export function usePersonaAdminStyle(): void {
  useInsertionEffect(() => {
    ensurePersonaAdminStyle();
  }, []);
}
