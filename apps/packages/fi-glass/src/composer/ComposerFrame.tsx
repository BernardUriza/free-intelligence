'use client';

/**
 * fi-glass · ComposerFrame — the composer's semantic anatomy
 * (B3-FIGLASS-COMPOSER-FRAME-1).
 *
 * The og118 canary audit found the zone above/around the composer growing by
 * accretion: every capability (voice draft, persona switch, call bar) stacked
 * its own sibling card, with no shared anatomy. The consensus anatomy across
 * the products that solved this (ChatGPT, Claude.ai, Gemini, WhatsApp; codified
 * by Vercel AI Elements' PromptInput) is ONE composer card with three zones:
 *
 *   header — previews/drafts (attachments, a recorded-audio draft)
 *   body   — the textarea row (required)
 *   footer — the controls row (tool chips left, voice/send right)
 *
 * The footer's LEFT rail is `footerStart` (B3-FIGLASS-COMPOSER-FOOTER-ZONES-1):
 * the tool-chip zone the anatomy above always described but the stylesheet made
 * unreachable, since a lone `justify-content: flex-end` pinned every control to
 * the right and left ~95% of the row dead. Consumers had nowhere to put a model
 * chip, an attach button or a call control, so each grew its own sibling card
 * above the box — the exact accretion this frame exists to prevent.
 *
 * `footerStart` claims the left rail with `margin-right: auto`, which beats the
 * container's `justify-content` without changing it. A footer with no
 * `footerStart` therefore renders byte-identically to before.
 *
 * This primitive owns ONLY that container + slot structure. It assumes nothing
 * about audio, personas, models or voice — consumers fill the slots. The body
 * renders WITHOUT a wrapper element so existing consumers' box layout is
 * byte-identical; header/footer wrappers exist only when the slot is filled.
 *
 * Spacing is tokenized against the density scale (`--fi-space-*`, from
 * densityStyle) with literal fallbacks for composers mounted outside an
 * `.fi-agent-workspace` root.
 */

import type { CSSProperties, ReactNode } from 'react';
import { useEffect } from 'react';

const COMPOSER_FRAME_STYLE_ID = 'fi-composer-frame-style';

const CSS = `
[data-fi-composer-slot="header"] {
  margin-bottom: var(--fi-space-2, 0.5rem);
}
[data-fi-composer-slot="footer"] {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--fi-space-2, 0.5rem);
}
[data-fi-composer-slot="footer-start"] {
  display: flex;
  align-items: center;
  gap: var(--fi-space-2, 0.5rem);
  min-width: 0;
  margin-right: auto;
}
`;

/** Inject the idempotent composer-frame stylesheet (no-op on the server / if already present). */
export function ensureComposerFrameStyle(): void {
  if (typeof document === 'undefined') return;
  if (document.getElementById(COMPOSER_FRAME_STYLE_ID)) return;
  const el = document.createElement('style');
  el.id = COMPOSER_FRAME_STYLE_ID;
  el.textContent = CSS;
  document.head.appendChild(el);
}

/** Ensure the composer-frame stylesheet is present for the lifetime of the component. */
export function useComposerFrameStyle(): void {
  useEffect(() => {
    ensureComposerFrameStyle();
  }, []);
}

export interface ComposerFrameProps {
  /** The body — the textarea row. Rendered directly (no wrapper element). */
  children: ReactNode;
  /** Optional header slot — previews/drafts above the body (e.g. an audio draft). */
  header?: ReactNode;
  /** Optional footer slot — the controls row below the body (chips, mic, send). */
  footer?: ReactNode;
  /**
   * Optional footer LEFT rail — tool chips (model/persona, attach, call). Claims
   * the left with `margin-right: auto`; omit it and the footer is unchanged.
   */
  footerStart?: ReactNode;
  /** Class for the single container (the consumer's frosted box preset). */
  className?: string;
  style?: CSSProperties;
  headerClassName?: string;
  footerClassName?: string;
  footerStyle?: CSSProperties;
  footerStartClassName?: string;
}

const filled = (slot: ReactNode) => slot != null && slot !== false;

export function ComposerFrame({
  children,
  header,
  footer,
  footerStart,
  className,
  style,
  headerClassName,
  footerClassName,
  footerStyle,
  footerStartClassName,
}: ComposerFrameProps) {
  useComposerFrameStyle();
  return (
    <div className={className} style={style} data-fi-composer-frame="">
      {filled(header) && (
        <div className={headerClassName} data-fi-composer-slot="header">
          {header}
        </div>
      )}
      {children}
      {(filled(footer) || filled(footerStart)) && (
        <div
          className={footerClassName}
          style={footerStyle}
          data-fi-composer-slot="footer"
        >
          {filled(footerStart) && (
            <div className={footerStartClassName} data-fi-composer-slot="footer-start">
              {footerStart}
            </div>
          )}
          {footer}
        </div>
      )}
    </div>
  );
}
