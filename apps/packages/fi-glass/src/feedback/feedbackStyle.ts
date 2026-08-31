'use client';

/**
 * fi-glass · the feedback layer.
 *
 * The package could draw an error inside a transcript and nowhere else, so
 * every consumer grew its own banner: a border colour, a padding and a red of
 * its own. The result is that the most important thing a surface ever says —
 * "this is wrong" — looked different on every screen of the same product.
 *
 * Same mechanism as {@link ../resource/resourceStyle} and
 * {@link ../form/formStyle}: ONE idempotent injected `<style>`, SSR-safe, every
 * literal interpolated from the token contract. Re-tint with `--fi-callout-*`.
 */

import { useEffect } from 'react';
import { glassTokens } from '../theme/glass-tokens.generated';

export const FI_CALLOUT_CLASS = 'fi-callout';
export const FI_CALLOUT_TITLE_CLASS = 'fi-callout-title';
export const FI_CALLOUT_BODY_CLASS = 'fi-callout-body';
export const FI_CALLOUT_LIST_CLASS = 'fi-callout-list';

const FEEDBACK_STYLE_ID = 'fi-feedback-style';

/* Tone is carried by `data-tone`, not by three near-identical classes: a
   consumer that wants a fourth tone sets two custom properties instead of
   waiting for a release. */
const CSS = `
.${FI_CALLOUT_CLASS} {
  --fi-callout-edge: var(--glass-chat-surface-border, ${glassTokens.surfaceBorder});
  --fi-callout-fill: var(--glass-chat-surface, ${glassTokens.surface});
  --fi-callout-ink: var(--glass-chat-text, ${glassTokens.text});
  border: 1px solid var(--fi-callout-edge);
  background: var(--fi-callout-fill);
  border-radius: var(--glass-chat-radius, ${glassTokens.radius});
  padding: 0.7rem 0.9rem;
}
.${FI_CALLOUT_CLASS}[data-tone='danger'] {
  --fi-callout-edge: var(--fi-callout-danger-edge, ${glassTokens.danger});
  --fi-callout-fill: var(--fi-callout-danger-fill, rgba(248, 113, 113, 0.08));
  --fi-callout-ink: var(--fi-callout-danger-edge, ${glassTokens.danger});
}
.${FI_CALLOUT_CLASS}[data-tone='warning'] {
  --fi-callout-edge: var(--fi-callout-warning-edge, #fbbf24);
  --fi-callout-fill: var(--fi-callout-warning-fill, rgba(251, 191, 36, 0.07));
  --fi-callout-ink: var(--fi-callout-warning-edge, #fbbf24);
}
.${FI_CALLOUT_CLASS}[data-tone='success'] {
  --fi-callout-edge: var(--fi-callout-success-edge, ${glassTokens.accent});
  --fi-callout-fill: var(--fi-callout-success-fill, rgba(52, 211, 153, 0.07));
  --fi-callout-ink: var(--fi-callout-success-edge, ${glassTokens.accent});
}
.${FI_CALLOUT_TITLE_CLASS} {
  display: block;
  margin-block-end: 0.4rem;
  font-size: ${glassTokens.itemMetaSize};
  font-weight: 700;
  letter-spacing: 0.4px;
  text-transform: uppercase;
  color: var(--fi-callout-ink);
}
.${FI_CALLOUT_BODY_CLASS} {
  color: var(--glass-chat-text, ${glassTokens.textBody});
  font-size: ${glassTokens.itemSubtitleSize};
}
.${FI_CALLOUT_LIST_CLASS} {
  margin: 0;
  padding-inline-start: 1.2rem;
  color: var(--glass-chat-text, ${glassTokens.textBody});
  font-size: ${glassTokens.itemSubtitleSize};
}
/* Entries arrive as prose with newlines — a cited clause, a measured figure.
   Collapsing them would run two sentences together and lose the citation. */
.${FI_CALLOUT_LIST_CLASS} li {
  margin-block-end: 0.4rem;
  white-space: pre-wrap;
}
.${FI_CALLOUT_LIST_CLASS} li:last-child {
  margin-block-end: 0;
}
`;

/** Inject the idempotent feedback stylesheet (no-op on the server / if already present). */
export function ensureFeedbackStyle(): void {
  if (typeof document === 'undefined') return;
  if (document.getElementById(FEEDBACK_STYLE_ID)) return;
  const el = document.createElement('style');
  el.id = FEEDBACK_STYLE_ID;
  el.textContent = CSS;
  document.head.appendChild(el);
}

/** Ensure the feedback stylesheet is present for the lifetime of the component. */
export function useFeedbackStyle(): void {
  useEffect(() => {
    ensureFeedbackStyle();
  }, []);
}
