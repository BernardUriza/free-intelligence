'use client';

/**
 * fi-glass · composer action anatomy (B3-FIGLASS-SHELL-PRIMITIVES-1D).
 *
 * Every control that lives on the composer — send, stop, a call chip, the "+" —
 * had been hand-rolling the same five declarations (flex centering, no shrink,
 * padding, radius, cursor) in whichever consumer rendered it. The og118 audit
 * counted that shape written three times in `globals.css` and once more inline
 * in `ComposerActions`, and each copy re-derived the 44×44 minimum for a narrow
 * composer by hand. That is anatomy, not branding, so it belongs here.
 *
 * The split this file draws, and it is the whole point: the framework owns the
 * SHAPE (box, spacing, icon size, touch minimum, what a label does when the
 * container gets narrow); the consumer owns the COLOR (its gradient, its
 * outline, its danger tint) through its own class. A primitive that shipped a
 * colour would make every shell look like og118 — the failure this arc exists
 * to prevent.
 *
 * The compact rules key off `@container fi-composer`, the same container
 * `ComposerFrame` collapses its rail in, so a control shrinks exactly when the
 * frame reflows — never off a viewport media query, which lies about a narrow
 * composer on a wide screen (`shell/touchTarget` is media-gated by design and
 * cannot serve this case).
 *
 * DEFAULTS are wrapped in `:where()` (specificity 0) and GUARANTEES are not.
 * This sheet is injected at runtime, so it lands in `<head>` AFTER the app's
 * stylesheet — at equal specificity the framework would win every tie, and the
 * first measured render proved it: `background: transparent` erased og118's send
 * gradient and the call chip's outline. A consumer's single class must beat a
 * framework default. The touch minimum is the deliberate exception: it keeps
 * real specificity so no consumer can shrink a target to win space back.
 */

import { useEffect } from 'react';

/** Base class for a composer control — compose it, never replace the consumer's class. */
export const FI_COMPOSER_ACTION_CLASS = 'fi-composer-action';

/** Variant classes: `primary` is the send-shaped square, `secondary` the pill chip. */
export const FI_COMPOSER_ACTION_VARIANT_CLASS = {
  primary: 'fi-composer-action--primary',
  secondary: 'fi-composer-action--secondary',
} as const;

export type ComposerActionVariant = keyof typeof FI_COMPOSER_ACTION_VARIANT_CLASS;

/** Class for the text beside a control's icon; hidden when the composer is compact. */
export const FI_COMPOSER_ACTION_LABEL_CLASS = 'fi-composer-action-label';

const COMPOSER_ACTION_STYLE_ID = 'fi-composer-action-style';

const CSS = `
:where(.${FI_COMPOSER_ACTION_CLASS}) {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  border: 1px solid transparent;
  background: transparent;
  color: inherit;
  cursor: pointer;
  transition: background 0.15s ease, border-color 0.15s ease, color 0.15s ease,
    box-shadow 0.15s ease, opacity 0.15s ease;
}
/* Unavailable, not absent: a disabled control keeps its box so the composer does
 * not reflow between empty and typed — the state a user sees most. */
:where(.${FI_COMPOSER_ACTION_CLASS}:disabled) {
  cursor: not-allowed;
}
:where(.${FI_COMPOSER_ACTION_CLASS}) svg {
  width: var(--fi-composer-action-icon-size, 1rem);
  height: var(--fi-composer-action-icon-size, 1rem);
}
:where(.${FI_COMPOSER_ACTION_VARIANT_CLASS.primary}) {
  padding: var(--fi-composer-action-padding, 0.5rem);
  border-radius: var(--fi-composer-action-radius, 10px);
}
:where(.${FI_COMPOSER_ACTION_VARIANT_CLASS.secondary}) {
  gap: var(--fi-composer-action-gap, 0.35rem);
  padding: var(--fi-composer-action-pill-padding, 0.3rem 0.65rem);
  border-radius: var(--fi-composer-action-pill-radius, 999px);
  font-size: var(--fi-composer-action-font-size, 0.8rem);
  font-weight: 600;
}
:where(.${FI_COMPOSER_ACTION_VARIANT_CLASS.secondary}) svg {
  width: var(--fi-composer-action-icon-size, 0.9rem);
  height: var(--fi-composer-action-icon-size, 0.9rem);
}
@container fi-composer (max-width: 420px) {
  /* Icon-only on a narrow composer, and icon-only still means a full touch
     target — never a chip shrunk to fit, which is how a control ends up
     orphaned on its own wrap line. Keyed off the CONTAINER because
     shell/touchTarget is viewport-gated and cannot see a narrow composer on a
     wide screen: there, send measured 34×34 against a 44 minimum. */
  .${FI_COMPOSER_ACTION_CLASS} {
    min-width: var(--fi-touch-target, 44px);
    min-height: var(--fi-touch-target, 44px);
  }
  :where(.${FI_COMPOSER_ACTION_VARIANT_CLASS.secondary}) {
    justify-content: center;
    padding: 0;
  }
  .${FI_COMPOSER_ACTION_LABEL_CLASS}[data-fi-compact-hide] {
    display: none;
  }
}
`;

/** Inject the idempotent composer-action stylesheet (no-op on the server / if already present). */
export function ensureComposerActionStyle(): void {
  if (typeof document === 'undefined') return;
  if (document.getElementById(COMPOSER_ACTION_STYLE_ID)) return;
  const el = document.createElement('style');
  el.id = COMPOSER_ACTION_STYLE_ID;
  el.textContent = CSS;
  document.head.appendChild(el);
}

/** Ensure the composer-action stylesheet is present for the lifetime of a control. */
export function useComposerActionStyle(): void {
  useEffect(() => {
    ensureComposerActionStyle();
  }, []);
}

/** Compose the action classes with an optional consumer class (additive, order-stable). */
export function withComposerAction(
  variant: ComposerActionVariant,
  className?: string,
): string {
  return [FI_COMPOSER_ACTION_CLASS, FI_COMPOSER_ACTION_VARIANT_CLASS[variant], className]
    .filter(Boolean)
    .join(' ');
}
