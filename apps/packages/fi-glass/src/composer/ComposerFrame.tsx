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
  /** Class for the single container (the consumer's frosted box preset). */
  className?: string;
  style?: CSSProperties;
  headerClassName?: string;
  footerClassName?: string;
  footerStyle?: CSSProperties;
}

export function ComposerFrame({
  children,
  header,
  footer,
  className,
  style,
  headerClassName,
  footerClassName,
  footerStyle,
}: ComposerFrameProps) {
  useComposerFrameStyle();
  return (
    <div className={className} style={style} data-fi-composer-frame="">
      {header != null && header !== false && (
        <div className={headerClassName} data-fi-composer-slot="header">
          {header}
        </div>
      )}
      {children}
      {footer != null && footer !== false && (
        <div
          className={footerClassName}
          style={footerStyle}
          data-fi-composer-slot="footer"
        >
          {footer}
        </div>
      )}
    </div>
  );
}
