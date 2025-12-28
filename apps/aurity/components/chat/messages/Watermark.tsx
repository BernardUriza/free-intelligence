'use client';

/**
 * Watermark - Single Responsibility: Background branding
 *
 * SOLID Principles:
 * - S: Only renders background watermark
 * - O: Configurable image, opacity, size
 */

import { memo } from 'react';

export interface WatermarkProps {
  /** Image URL */
  src?: string;
  /** Opacity (0-1) */
  opacity?: number;
  /** Is visible? */
  visible: boolean;
}

export const Watermark = memo(function Watermark({
  src = '/images/fi.png',
  opacity = 0.02, // Casi invisible (was 0.06)
  visible,
}: WatermarkProps) {
  if (!visible) return null;

  return (
    <div
      aria-hidden="true"
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundImage: `url(${src})`,
        backgroundSize: 'contain',
        backgroundPosition: 'center',
        backgroundRepeat: 'no-repeat',
        opacity,
        pointerEvents: 'none',
        zIndex: 0,
        filter: 'blur(1px)', // Suavizar aún más
      }}
    />
  );
});
