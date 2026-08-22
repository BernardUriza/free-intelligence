'use client';

/**
 * fi-glass · a usage bar with an honest unbounded state.
 *
 * `max == null` means NO CEILING, and the component refuses to draw a bar for it:
 * there is no such thing as a percentage of unlimited. It renders the usage on
 * its own instead, so the reader learns the true thing ("40 documents") rather
 * than a comforting fraction of an invented denominator. That mirrors the server
 * contract exactly — `maxBytes: null` travels the wire meaning unlimited, and
 * inventing a ceiling here would launder it back into a number.
 *
 * `max === 0` is not unlimited: nothing fits, so it is 100% full and says so.
 */

import { type ReactNode } from 'react';
import {
  FI_METER_CLASS,
  FI_METER_FILL_CLASS,
  FI_METER_LABEL_CLASS,
  FI_METER_TRACK_CLASS,
  useResourceStyle,
} from './resourceStyle';

export interface CapacityMeterProps {
  used: number;
  /** The ceiling, or `null`/`undefined` for no ceiling — the bar is then omitted. */
  max?: number | null;
  /**
   * Renders the text. Receives the computed percentage, or `null` when unbounded
   * — so the consumer writes its own words ("40 documents", "no limit") and
   * fi-glass never ships a language.
   */
  label: (percent: number | null) => ReactNode;
  className?: string;
}

export function CapacityMeter({ used, max, label, className }: CapacityMeterProps) {
  useResourceStyle();
  const bounded = max != null;
  // Clamped: a corpus over its quota (the ceiling was lowered under it) must
  // render a full bar, never one that overflows its track.
  const percent = bounded ? clamp(max === 0 ? 100 : (used / max) * 100) : null;
  return (
    <div className={className ? `${FI_METER_CLASS} ${className}` : FI_METER_CLASS}>
      {percent != null && (
        <div
          className={FI_METER_TRACK_CLASS}
          role="progressbar"
          aria-valuenow={Math.round(percent)}
          aria-valuemin={0}
          aria-valuemax={100}
        >
          <div className={FI_METER_FILL_CLASS} style={{ width: `${percent}%` }} />
        </div>
      )}
      <span className={FI_METER_LABEL_CLASS}>{label(percent)}</span>
    </div>
  );
}

function clamp(value: number): number {
  if (!Number.isFinite(value) || value < 0) return 0;
  return value > 100 ? 100 : value;
}
