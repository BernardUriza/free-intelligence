'use client';

/**
 * fi-glass · touch-target minimums (B3-FIGLASS-MOBILE-2).
 *
 * The og118 mobile canary (kids tapping on phones in the papelería) measured
 * every primary control below the 44×44 CSS-px touch minimum: mic 32, send 34,
 * SpeakButton 26, CopyButton 20, the drawer hamburger 36. Rather than each
 * control hand-rolling a min-size — or a consumer patching it in app CSS — the
 * framework owns ONE idempotent touch primitive: an injected <style> that gives
 * `.fi-touch-target` a 44×44 minimum hit area, gated to mobile/touch so a desktop
 * with a fine pointer is never inflated.
 *
 * Compose {@link FI_TOUCH_TARGET_CLASS} onto a control's className (it is
 * ADDITIVE — never replaces the consumer's class) and call
 * {@link useTouchTargetStyle} once in the component so the stylesheet is present.
 * The class is exported so consumers (e.g. og118's sidebar "Nuevo chat"/"Borrar")
 * inherit the SAME framework minimum instead of authoring their own.
 */

import { useInsertionEffect } from 'react';
import { FI_TOUCH_QUERY } from '../theme/breakpoints';

export const FI_TOUCH_TARGET_CLASS = 'fi-touch-target';

const TOUCH_TARGET_STYLE_ID = 'fi-touch-target-style';

/** Inject the idempotent touch-target stylesheet (no-op on the server / if already present). */
export function ensureTouchTargetStyle(): void {
  if (typeof document === 'undefined') return;
  if (document.getElementById(TOUCH_TARGET_STYLE_ID)) return;
  const el = document.createElement('style');
  el.id = TOUCH_TARGET_STYLE_ID;
  // The 44×44 minimum is a guarantee; the centering is a default for icon controls
  // that a component with its own layout (a card) overrides with one class.
  el.textContent = `
    @media ${FI_TOUCH_QUERY} {
      .${FI_TOUCH_TARGET_CLASS} {
        min-width: var(--fi-touch-target, 44px);
        min-height: var(--fi-touch-target, 44px);
        box-sizing: border-box;
      }
      :where(.${FI_TOUCH_TARGET_CLASS}) {
        display: inline-flex;
        align-items: center;
        justify-content: center;
      }
    }
  `;
  document.head.appendChild(el);
}

/** Ensure the touch-target stylesheet is present for the lifetime of a control. */
export function useTouchTargetStyle(): void {
  useInsertionEffect(() => {
    ensureTouchTargetStyle();
  }, []);
}

/** Compose {@link FI_TOUCH_TARGET_CLASS} with an optional consumer class (additive, order-stable). */
export function withTouchTarget(className?: string): string {
  return className ? `${FI_TOUCH_TARGET_CLASS} ${className}` : FI_TOUCH_TARGET_CLASS;
}
