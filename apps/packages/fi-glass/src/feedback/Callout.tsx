'use client';

/**
 * fi-glass · a callout, and a list of them.
 *
 * `CalloutList` exists because the shape it draws keeps being rebuilt by hand:
 * a heading plus N reasons, where each reason is a whole sentence that must
 * survive intact. Two rules are baked in rather than left to the caller:
 *
 * 1. **Empty renders nothing.** A titled box with no entries reads as a system
 *    that has an opinion and will not say it. Callers pass whatever they have
 *    and stop writing `items.length > 0 &&` at every site.
 * 2. **The order is never touched.** Callers order these lists deliberately —
 *    the entry that changes a decision goes first — and a component that sorted
 *    them would silently overrule that.
 */

import { type ReactNode } from 'react';
import {
  FI_CALLOUT_BODY_CLASS,
  FI_CALLOUT_CLASS,
  FI_CALLOUT_LIST_CLASS,
  FI_CALLOUT_TITLE_CLASS,
  useFeedbackStyle,
} from './feedbackStyle';

export type CalloutTone = 'neutral' | 'danger' | 'warning' | 'success';

export interface CalloutProps {
  children: ReactNode;
  tone?: CalloutTone;
  title?: ReactNode;
  /**
   * Announce it the moment it appears. Default: `true` for `danger`.
   * A wrong value the reader is never told about is the failure this guards.
   */
  live?: boolean;
  className?: string;
}

export function Callout({ children, tone = 'neutral', title, live, className }: CalloutProps) {
  useFeedbackStyle();
  const anuncia = live ?? tone === 'danger';
  return (
    <div
      className={className ? `${FI_CALLOUT_CLASS} ${className}` : FI_CALLOUT_CLASS}
      data-tone={tone === 'neutral' ? undefined : tone}
      role={anuncia ? 'alert' : undefined}
    >
      {title ? <strong className={FI_CALLOUT_TITLE_CLASS}>{title}</strong> : null}
      <div className={FI_CALLOUT_BODY_CLASS}>{children}</div>
    </div>
  );
}

export interface CalloutListProps {
  /** Rendered in the given order, always. Empty renders nothing at all. */
  items: ReactNode[];
  tone?: CalloutTone;
  title?: ReactNode;
  live?: boolean;
  className?: string;
}

export function CalloutList({ items, tone, title, live, className }: CalloutListProps) {
  if (!items.length) return null;
  return (
    <Callout tone={tone} title={title} live={live} className={className}>
      <ul className={FI_CALLOUT_LIST_CLASS}>
        {items.map((item, i) => (
          <li key={i}>{item}</li>
        ))}
      </ul>
    </Callout>
  );
}
