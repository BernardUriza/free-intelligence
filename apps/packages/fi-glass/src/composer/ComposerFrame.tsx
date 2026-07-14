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
import { useEffect, useId, useState } from 'react';
import { SlidersHorizontal } from 'lucide-react';
import { withTouchTarget } from '../shell/touchTarget';

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
/* A consumer's aboveComposer is usually a fragment of conditional banners, so it
 * is ALWAYS truthy and its wrapper mounts even with nothing inside — leaving a
 * ghost row of margin above the box. Collapse it when it renders empty. */
.fi-surface-above-composer:empty {
  display: none;
}
/* CONV-MOBILE-RECLAIM-1 — compact composer on narrow containers.
 *
 * Wide (desktop) is byte-identical: the rail toggle stays display:none and the
 * body/footer keep their stacked anatomy. At <=420px container width the frame
 * becomes ONE wrapping flex row — [toggle] [textarea] [mic] [send] — and the
 * footer-start rail (persona chip, call, attach) collapses behind the toggle,
 * expanding as its own full-width row under the input. Send stays the single
 * always-visible primary action; the textarea still grows to maxRows. */
.fi-composer-rail-toggle {
  display: none;
  align-items: center;
  justify-content: center;
  border: none;
  background: transparent;
  color: var(--fi-sidebar-item-action-color, #64748b);
  cursor: pointer;
  padding: 0;
  border-radius: 8px;
}
.fi-composer-rail-toggle[aria-expanded="true"] {
  color: var(--glass-chat-accent-text, #6ee7b7);
  background: rgba(255, 255, 255, 0.06);
}
@container fi-composer (max-width: 420px) {
  [data-fi-composer-frame] {
    display: flex;
    flex-wrap: wrap;
    align-items: flex-end;
    gap: 0.375rem;
  }
  [data-fi-composer-slot="header"] {
    flex: 1 1 100%;
    order: -2;
    margin-bottom: 0;
  }
  [data-fi-composer-slot="footer"] {
    display: contents;
  }
  /* The body (whatever wrapper the consumer's Composer renders) becomes the
     row's flexing member so the textarea shares the line with toggle/mic/send. */
  [data-fi-composer-frame] > :not([data-fi-composer-slot]) {
    flex: 1 1 0%;
    min-width: 0;
  }
  .fi-composer-rail-toggle {
    display: inline-flex;
    order: -1;
  }
  [data-fi-composer-slot="footer-start"] {
    flex: 1 1 100%;
    order: 5;
    flex-wrap: wrap;
    margin-right: 0;
  }
  [data-fi-composer-frame][data-fi-rail="closed"] [data-fi-composer-slot="footer-start"] {
    display: none;
  }
  /* A control marked data-fi-rail-keep survives the collapse — the contract for
     "this is live and the user must keep reaching it" (e.g. the hang-up button
     of an ACTIVE voice call). The closed rail then stays rendered inline on the
     input row but shows ONLY the kept controls. */
  [data-fi-composer-frame][data-fi-rail="closed"] [data-fi-composer-slot="footer-start"]:has([data-fi-rail-keep]) {
    display: flex;
    flex: 0 0 auto;
    order: 0;
    margin-right: 0;
  }
  /* !important on purpose: slotted controls (e.g. ComposerActions' trigger)
     carry inline display styles that outrank any selector — and the collapse
     contract must win over a control's own presentation. */
  [data-fi-composer-frame][data-fi-rail="closed"] [data-fi-composer-slot="footer-start"]:has([data-fi-rail-keep]) > :not([data-fi-rail-keep]) {
    display: none !important;
  }
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
  /** Accessible label for the compact-mode rail disclosure toggle
   * (CONV-MOBILE-RECLAIM-1). Only rendered when `footerStart` is filled. */
  railToggleLabel?: string;
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
  railToggleLabel = 'Más opciones',
}: ComposerFrameProps) {
  useComposerFrameStyle();
  // Compact-mode rail disclosure (CONV-MOBILE-RECLAIM-1). Collapsed on every
  // mount (no persistence — Ockham); the toggle itself only becomes visible
  // when the fi-composer container is narrow, so desktop never sees it.
  const [railOpen, setRailOpen] = useState(false);
  const railId = useId();
  const hasRail = filled(footerStart);
  return (
    <div
      className={className}
      style={style}
      data-fi-composer-frame=""
      data-fi-rail={hasRail ? (railOpen ? 'open' : 'closed') : undefined}
    >
      {filled(header) && (
        <div className={headerClassName} data-fi-composer-slot="header">
          {header}
        </div>
      )}
      {children}
      {(filled(footer) || hasRail) && (
        <div
          className={footerClassName}
          style={footerStyle}
          data-fi-composer-slot="footer"
        >
          {hasRail && (
            <>
              <button
                type="button"
                className={withTouchTarget('fi-composer-rail-toggle')}
                aria-label={railToggleLabel}
                aria-expanded={railOpen}
                aria-controls={railId}
                onClick={() => setRailOpen((v) => !v)}
              >
                <SlidersHorizontal size={18} aria-hidden />
              </button>
              <div
                id={railId}
                className={footerStartClassName}
                data-fi-composer-slot="footer-start"
              >
                {footerStart}
              </div>
            </>
          )}
          {footer}
        </div>
      )}
    </div>
  );
}
