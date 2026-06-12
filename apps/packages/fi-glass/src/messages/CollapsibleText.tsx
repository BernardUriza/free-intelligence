'use client';

/**
 * fi-glass · CollapsibleText — ChatGPT-style disclosure clamp for long content.
 *
 * Long content is clamped to `maxHeight` with a CSS mask-image gradient fading
 * out the last `fadeHeight` pixels (the text itself fades — no overlay), plus a
 * "show more / show less" toggle wired as a WAI-ARIA disclosure
 * (aria-expanded + aria-controls). Reverse-engineered from chatgpt.com's
 * collapsed user messages (max-height 264px = 11 lines × 24px leading,
 * mask-image linear-gradient over the final 48px).
 *
 * Measurement is content-driven: a ResizeObserver compares scrollHeight against
 * the clamp, so the toggle only renders when the content actually overflows.
 * SSR-safe — the first paint renders unclamped and clamps on mount.
 */

import { useEffect, useId, useRef, useState, type ReactNode } from 'react';

export interface CollapsibleTextProps {
  children: ReactNode;
  /** Collapsed max height in px. Default 264 (11 lines at 24px leading). */
  maxHeight?: number;
  /** Height in px of the fade-out mask at the bottom of clamped content. Default 48. */
  fadeHeight?: number;
  /** Toggle copy when collapsed. Default: "Mostrar más". */
  showMoreLabel?: string;
  /** Toggle copy when expanded. Default: "Mostrar menos". */
  showLessLabel?: string;
  /** Wrapper class (style hook for the app). */
  className?: string;
  /** Toggle button class. When set, the unstyled default is dropped. */
  toggleClassName?: string;
}

export function CollapsibleText({
  children,
  maxHeight = 264,
  fadeHeight = 48,
  showMoreLabel = 'Mostrar más',
  showLessLabel = 'Mostrar menos',
  className,
  toggleClassName,
}: CollapsibleTextProps) {
  const contentId = useId();
  const contentRef = useRef<HTMLDivElement>(null);
  const [expanded, setExpanded] = useState(false);
  const [overflowing, setOverflowing] = useState(false);

  useEffect(() => {
    const el = contentRef.current;
    if (!el) return;
    // 16px tolerance: a message one line over the clamp reads better whole than
    // clamped with a toggle that reveals a single hidden line.
    const measure = () => setOverflowing(el.scrollHeight > maxHeight + 16);
    measure();
    if (typeof ResizeObserver === 'undefined') return;
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, [maxHeight]);

  const clamped = overflowing && !expanded;
  const mask = `linear-gradient(rgb(0,0,0) calc(100% - ${fadeHeight}px), transparent)`;

  return (
    <div className={className}>
      <div
        id={contentId}
        ref={contentRef}
        style={
          clamped
            ? {
                maxHeight,
                overflow: 'hidden',
                maskImage: mask,
                WebkitMaskImage: mask,
              }
            : undefined
        }
      >
        {children}
      </div>
      {overflowing && (
        <button
          type="button"
          aria-expanded={expanded}
          aria-controls={contentId}
          onClick={() => setExpanded((e) => !e)}
          className={toggleClassName}
          style={
            toggleClassName
              ? undefined
              : {
                  marginTop: '0.25rem',
                  padding: 0,
                  border: 'none',
                  background: 'transparent',
                  color: '#94a3b8',
                  fontSize: '0.8rem',
                  cursor: 'pointer',
                  textDecoration: 'underline',
                  textUnderlineOffset: 2,
                }
          }
        >
          {expanded ? showLessLabel : showMoreLabel}
        </button>
      )}
    </div>
  );
}
