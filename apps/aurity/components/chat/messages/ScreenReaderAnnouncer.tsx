'use client';

/**
 * ScreenReaderAnnouncer - Single Responsibility: A11y announcements
 *
 * SOLID Principles:
 * - S: Only handles screen reader announcements
 * - O: Configurable politeness level
 * - D: Receives announcement text, doesn't compute it
 */

import { memo, useRef, useEffect } from 'react';

export interface ScreenReaderAnnouncerProps {
  /** Text to announce */
  announcement: string;
  /** Politeness level */
  politeness?: 'polite' | 'assertive';
}

export const ScreenReaderAnnouncer = memo(function ScreenReaderAnnouncer({
  announcement,
  politeness = 'polite',
}: ScreenReaderAnnouncerProps) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (announcement && ref.current) {
      ref.current.textContent = announcement;
    }
  }, [announcement]);

  return (
    <div
      ref={ref}
      aria-live={politeness}
      aria-atomic="true"
      className="sr-only"
      role="status"
    />
  );
});
