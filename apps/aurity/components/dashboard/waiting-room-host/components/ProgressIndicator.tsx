'use client';

/**
 * ProgressIndicator - Dots showing current position in content rotation
 */

import { memo } from 'react';

interface ProgressIndicatorProps {
  /** Total number of items */
  total: number;
  /** Current active index */
  current: number;
}

export const ProgressIndicator = memo(function ProgressIndicator({
  total,
  current,
}: ProgressIndicatorProps) {
  if (total === 0) return null;

  return (
    <div className="mt-auto pt-2 sm:pt-3 flex items-center gap-1 sm:gap-2 flex-shrink-0">
      {Array.from({ length: total }).map((_, index) => (
        <div
          key={index}
          className={`h-1 flex-1 rounded-full transition-all duration-300 ${
            index === current
              ? 'bg-purple-500'
              : index < current
              ? 'bg-purple-700'
              : 'bg-slate-700'
          }`}
        />
      ))}
    </div>
  );
});
