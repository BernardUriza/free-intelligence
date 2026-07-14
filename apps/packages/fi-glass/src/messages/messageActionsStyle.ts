'use client';

/**
 * fi-glass · per-message actions reveal (CONV-MOBILE-RECLAIM-1).
 *
 * The actions row (copy, speak, whatever the consumer injects) must not spend
 * permanent viewport on every message. One injected idempotent sheet — same
 * present-once SSR-safe mechanism as sidebarItemStyle — owns the reveal:
 *
 *  - Fine pointers (desktop): the row keeps its space (no layout shift) and
 *    fades in on row hover or when any action has keyboard focus.
 *  - Coarse pointers (touch): the row is collapsed entirely and appears for
 *    (a) the LAST message of the thread — the one acted on most, always ready —
 *    (b) a row the user tapped (`data-fi-actions-open`, toggled by the bubble).
 *
 * Buttons keep their aria-labels and DOM presence on fine pointers, so
 * keyboard/screen-reader flows are unchanged where they exist.
 */

import { useEffect } from 'react';

export const FI_MSG_ACTIONS_CLASS = 'fi-msg-actions';

const MESSAGE_ACTIONS_STYLE_ID = 'fi-msg-actions-style';

const CSS = `
.${FI_MSG_ACTIONS_CLASS} {
  margin-top: 0.25rem;
}
@media (hover: hover) and (pointer: fine) {
  .${FI_MSG_ACTIONS_CLASS} {
    opacity: 0;
    transition: opacity 0.15s ease;
  }
  article:hover > .${FI_MSG_ACTIONS_CLASS},
  .${FI_MSG_ACTIONS_CLASS}:focus-within {
    opacity: 1;
  }
}
@media (pointer: coarse) {
  .${FI_MSG_ACTIONS_CLASS} {
    display: none;
  }
  article[data-fi-last-message] > .${FI_MSG_ACTIONS_CLASS},
  article[data-fi-actions-open] > .${FI_MSG_ACTIONS_CLASS} {
    display: block;
  }
}
`;

/** Inject the idempotent message-actions stylesheet (no-op on the server / if present). */
export function ensureMessageActionsStyle(): void {
  if (typeof document === 'undefined') return;
  if (document.getElementById(MESSAGE_ACTIONS_STYLE_ID)) return;
  const el = document.createElement('style');
  el.id = MESSAGE_ACTIONS_STYLE_ID;
  el.textContent = CSS;
  document.head.appendChild(el);
}

/** Ensure the message-actions stylesheet is present for the component's lifetime. */
export function useMessageActionsStyle(): void {
  useEffect(() => {
    ensureMessageActionsStyle();
  }, []);
}
