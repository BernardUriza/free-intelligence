'use client';

/**
 * fi-glass · the form layer.
 *
 * fi-glass grew as the skin of a conversational surface, so until now it had no
 * way to ask a person for a value: no field, no input, no select, no checkbox.
 * Every consumer that needed one wrote its own `<input>` with its own colors,
 * which is how a design system quietly stops being one — the chat looks like
 * fi-glass and the form looks like whoever typed it that afternoon.
 *
 * Same mechanism as {@link ../resource/resourceStyle}: ONE idempotent injected
 * `<style>`, SSR-safe, every literal interpolated from the token contract
 * instead of typed by hand. A consumer re-tints by setting `--fi-field-*` on an
 * ancestor; it never copies a class up and never edits this file.
 *
 * The invalid state is drawn from `glassTokens.danger`, the same red the rest of
 * the package uses, so an error in a form and an error in a transcript are
 * recognisably the same event.
 */

import { useEffect } from 'react';
import { glassTokens } from '../theme/glass-tokens.generated';

export const FI_FIELD_CLASS = 'fi-field';
export const FI_FIELD_LABEL_CLASS = 'fi-field-label';
export const FI_FIELD_CONTROL_CLASS = 'fi-field-control';
export const FI_FIELD_HINT_CLASS = 'fi-field-hint';
export const FI_FIELD_ERROR_CLASS = 'fi-field-error';
export const FI_FIELD_GRID_CLASS = 'fi-field-grid';
export const FI_CHECKBOX_CLASS = 'fi-field-checkbox';
export const FI_CHECKBOX_LABEL_CLASS = 'fi-field-checkbox-label';
export const FI_FORM_ACTIONS_CLASS = 'fi-form-actions';
export const FI_BUTTON_CLASS = 'fi-button';
export const FI_BUTTON_QUIET_CLASS = 'fi-button-quiet';
export const FI_BUTTON_DANGER_CLASS = 'fi-button-danger';

const FORM_STYLE_ID = 'fi-form-style';

/* The control height is the touch target, not a smaller number that happens to
   look right on a desktop: a field a finger cannot hit is a field that gets
   filled wrong. 44px is the same constant `shell/touchTarget` already uses. */
const CSS = `
.${FI_FIELD_CLASS} {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  min-width: 0;
}
.${FI_FIELD_LABEL_CLASS} {
  font-size: var(--fi-field-label-size, ${glassTokens.itemMetaSize});
  letter-spacing: 0.3px;
  text-transform: uppercase;
  color: var(--fi-field-label-color, var(--glass-chat-text-muted, ${glassTokens.textMuted}));
}
.${FI_FIELD_LABEL_CLASS}[data-required]::after {
  content: '*';
  color: var(--fi-field-invalid, ${glassTokens.danger});
  margin-inline-start: 0.2em;
}
.${FI_FIELD_CONTROL_CLASS} {
  width: 100%;
  min-height: var(--fi-touch-target, 44px);
  padding: 0.45rem 0.6rem;
  font: inherit;
  color: var(--glass-chat-text, ${glassTokens.text});
  background: var(--fi-field-fill, ${glassTokens.searchFill});
  border: 1px solid var(--fi-field-border, ${glassTokens.searchBorder});
  border-radius: var(--fi-field-radius, ${glassTokens.itemRadius});
}
textarea.${FI_FIELD_CONTROL_CLASS} {
  min-height: 5rem;
  resize: vertical;
}
.${FI_FIELD_CONTROL_CLASS}::placeholder {
  color: var(--glass-chat-text-muted, ${glassTokens.textFaint});
}
.${FI_FIELD_CONTROL_CLASS}:focus-visible {
  outline: 2px solid var(--fi-accent, ${glassTokens.accentText});
  outline-offset: 1px;
}
.${FI_FIELD_CONTROL_CLASS}:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
.${FI_FIELD_CONTROL_CLASS}[aria-invalid='true'] {
  border-color: var(--fi-field-invalid, ${glassTokens.danger});
}
.${FI_FIELD_HINT_CLASS} {
  font-size: ${glassTokens.itemMetaSize};
  color: var(--glass-chat-text-muted, ${glassTokens.textMuted});
}
.${FI_FIELD_ERROR_CLASS} {
  font-size: ${glassTokens.itemMetaSize};
  color: var(--fi-field-invalid, ${glassTokens.danger});
}
.${FI_FIELD_GRID_CLASS} {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(var(--fi-field-min, 12rem), 1fr));
  gap: var(--fi-field-gap, 0.75rem);
}
.${FI_CHECKBOX_CLASS} {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  min-height: var(--fi-touch-target, 44px);
}
.${FI_CHECKBOX_CLASS} input {
  inline-size: 1rem;
  block-size: 1rem;
  accent-color: var(--fi-accent, ${glassTokens.accent});
}
.${FI_CHECKBOX_LABEL_CLASS} {
  font-size: ${glassTokens.itemSubtitleSize};
  color: var(--glass-chat-text, ${glassTokens.textBody});
}
.${FI_FORM_ACTIONS_CLASS} {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.6rem;
}
.${FI_BUTTON_CLASS} {
  min-height: var(--fi-touch-target, 44px);
  padding: 0.5rem 1.1rem;
  font: inherit;
  font-weight: 600;
  color: var(--fi-button-text, ${glassTokens.sendText});
  background-image: linear-gradient(
    to right,
    var(--glass-chat-accent-from, ${glassTokens.accentDeep}),
    var(--glass-chat-accent-to, ${glassTokens.accentTo})
  );
  border: 0;
  border-radius: var(--fi-field-radius, ${glassTokens.itemRadius});
  cursor: pointer;
}
.${FI_BUTTON_CLASS}:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.${FI_BUTTON_CLASS}:focus-visible {
  outline: 2px solid var(--fi-accent, ${glassTokens.accentText});
  outline-offset: 2px;
}
.${FI_BUTTON_QUIET_CLASS} {
  background-image: none;
  background: transparent;
  color: var(--fi-accent, ${glassTokens.accentText});
  border: 1px solid var(--fi-field-border, ${glassTokens.surfaceBorder});
}
.${FI_BUTTON_DANGER_CLASS} {
  background-image: none;
  background: transparent;
  color: var(--fi-field-invalid, ${glassTokens.danger});
  border: 1px solid var(--fi-field-invalid, ${glassTokens.danger});
}
`;

/** Inject the idempotent form stylesheet (no-op on the server / if already present). */
export function ensureFormStyle(): void {
  if (typeof document === 'undefined') return;
  if (document.getElementById(FORM_STYLE_ID)) return;
  const el = document.createElement('style');
  el.id = FORM_STYLE_ID;
  el.textContent = CSS;
  document.head.appendChild(el);
}

/** Ensure the form stylesheet is present for the lifetime of the component. */
export function useFormStyle(): void {
  useEffect(() => {
    ensureFormStyle();
  }, []);
}
