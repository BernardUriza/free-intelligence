'use client';

/**
 * fi-glass · the surface layer: panels, notes, literals, data tables.
 *
 * Born from the consulta-medica canary the same way `form` and `feedback`
 * were: its stylesheet grew a hand-rolled section card (`cm-tarjeta`), a
 * muted note, a monospace literal block and a bordered data table, each one
 * built FROM the glass tokens but living outside the package — so the next
 * consumer would have rebuilt all four. These are the pieces a page made of
 * sections needs, as opposed to a page made of chat.
 *
 * Same mechanism as {@link ../feedback/feedbackStyle}: ONE idempotent
 * injected `<style>`, SSR-safe, every literal interpolated from the token
 * contract. Re-tint with the `--glass-chat-*` custom properties.
 */

import { useEffect } from 'react';
import { glassTokens } from '../theme/glass-tokens.generated';

export const FI_PANEL_CLASS = 'fi-panel';
export const FI_PANEL_TITLE_CLASS = 'fi-panel-title';
export const FI_NOTE_CLASS = 'fi-note';
export const FI_LITERAL_CLASS = 'fi-literal';
export const FI_DATA_TABLE_CLASS = 'fi-data-table';
export const FI_LITERAL_INLINE_CLASS = 'fi-literal-inline';
export const FI_NOTE_INLINE_CLASS = 'fi-note-inline';

const SURFACE_STYLE_ID = 'fi-surface-style';

const CSS = `
.${FI_PANEL_CLASS} {
  background: var(--glass-chat-surface, ${glassTokens.surface});
  border: 1px solid var(--glass-chat-surface-border, ${glassTokens.surfaceBorder});
  border-radius: var(--glass-chat-radius, ${glassTokens.radius});
  padding: 1rem 1.5rem;
  margin-block-end: 1rem;
  box-shadow: var(--glass-chat-shadow, ${glassTokens.shadow});
}
.${FI_PANEL_TITLE_CLASS} {
  margin: 0 0 0.5rem;
  font-size: ${glassTokens.itemMetaSize};
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.4px;
  color: var(--glass-chat-accent-text, ${glassTokens.accentText});
}
/* Actions inside a panel breathe on their own; outside one, the form layer
   already spaces them. Scoped here so the form layer stays panel-agnostic. */
.${FI_PANEL_CLASS} .fi-form-actions {
  margin-block-start: 1rem;
}
.${FI_NOTE_CLASS} {
  color: var(--glass-chat-text-muted, ${glassTokens.textMuted});
  font-size: ${glassTokens.itemSubtitleSize};
}
/* Server-rendered text shown VERBATIM — a privacy preview, a streamed draft.
   pre-wrap because the whole point is that nothing gets reflowed away. */
.${FI_LITERAL_CLASS} {
  font-family: ui-monospace, 'SF Mono', Menlo, monospace;
  font-size: 13px;
  background: var(--glass-chat-bubble-assistant, ${glassTokens.bubbleAssistant});
  border: 1px solid var(--glass-chat-surface-border, ${glassTokens.surfaceBorder});
  border-radius: 10px;
  padding: 0.75rem;
  white-space: pre-wrap;
}
/* The inline twins: a verbatim fragment quoted MID-SENTENCE (a cited phrase
   from a source document) and a muted aside that must not break the line.
   Block Literal/Note render <pre>/<p>; these render <span>, because a block
   element inside a paragraph is invalid HTML and React will say so. */
.${FI_LITERAL_INLINE_CLASS} {
  font-family: ui-monospace, 'SF Mono', Menlo, monospace;
  font-size: 0.92em;
  background: var(--glass-chat-bubble-assistant, ${glassTokens.bubbleAssistant});
  border: 1px solid var(--glass-chat-surface-border, ${glassTokens.surfaceBorder});
  border-radius: 6px;
  padding: 0 0.3rem;
  white-space: pre-wrap;
}
.${FI_NOTE_INLINE_CLASS} {
  color: var(--glass-chat-text-muted, ${glassTokens.textMuted});
  font-size: ${glassTokens.itemSubtitleSize};
}
.${FI_DATA_TABLE_CLASS} {
  width: 100%;
  border-collapse: collapse;
  font-size: ${glassTokens.itemSubtitleSize};
}
.${FI_DATA_TABLE_CLASS} th,
.${FI_DATA_TABLE_CLASS} td {
  border: 1px solid var(--glass-chat-surface-border, ${glassTokens.surfaceBorder});
  padding: 6px 8px;
  text-align: left;
}
.${FI_DATA_TABLE_CLASS} th {
  background: var(--glass-chat-bubble-assistant, ${glassTokens.bubbleAssistant});
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.3px;
  color: var(--glass-chat-text-muted, ${glassTokens.textMuted});
}
`;

/** Inject the idempotent surface stylesheet (no-op on the server / if already present). */
export function ensureSurfaceStyle(): void {
  if (typeof document === 'undefined') return;
  if (document.getElementById(SURFACE_STYLE_ID)) return;
  const el = document.createElement('style');
  el.id = SURFACE_STYLE_ID;
  el.textContent = CSS;
  document.head.appendChild(el);
}

/** Ensure the surface stylesheet is present for the lifetime of the component. */
export function useSurfaceStyle(): void {
  useEffect(() => {
    ensureSurfaceStyle();
  }, []);
}
