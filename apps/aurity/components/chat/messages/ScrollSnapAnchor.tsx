'use client';

/**
 * ScrollSnapAnchor - Single Responsibility: CSS scroll-snap target
 *
 * SOLID Principles:
 * - S: Only provides scroll-snap anchor point
 * - O: Configurable alignment
 */

import { memo } from 'react';

export interface ScrollSnapAnchorProps {
  /** Snap alignment */
  align?: 'start' | 'center' | 'end';
}

export const ScrollSnapAnchor = memo(function ScrollSnapAnchor({
  align = 'end',
}: ScrollSnapAnchorProps) {
  return (
    <div
      aria-hidden="true"
      style={{
        scrollSnapAlign: align,
        height: 1,
        // Invisible but takes space for snap calculation
      }}
    />
  );
});
