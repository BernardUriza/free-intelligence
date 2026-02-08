/**
 * RecordingTimer - Shared Timer Display Component
 *
 * Displays recording time in MM:SS format.
 * Used by: RecordingControls, VoiceMicButton
 *
 * Features:
 * - Multiple size variants
 * - Optional recording dot indicator
 * - Configurable colors
 */

'use client';

import { motion } from 'framer-motion';

export interface RecordingTimerProps {
  /** Time in seconds */
  time: number;
  /** Whether to show the timer */
  visible?: boolean;
  /** Size variant */
  size?: 'sm' | 'md' | 'lg';
  /** Show blinking recording dot */
  showDot?: boolean;
  /** Text color (domain class) */
  textColor?: string;
  /** Dot color (domain class) */
  dotColor?: string;
  /** Additional classes */
  className?: string;
}

/**
 * Format seconds to MM:SS string
 */
export function formatRecordingTime(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

const SIZE_CLASSES = {
  sm: 'rec-timer-sm',
  md: 'rec-timer-md',
  lg: 'rec-timer-lg',
};

export function RecordingTimer({
  time,
  visible = true,
  size = 'md',
  showDot = false,
  textColor = 'rec-timer-text-white',
  dotColor = 'rec-timer-dot-red',
  className = '',
}: RecordingTimerProps) {
  if (!visible || time <= 0) return null;

  return (
    <div className={`rec-timer-wrap ${SIZE_CLASSES[size]} ${className}`}>
      {showDot && (
        <motion.div
          className={`rec-timer-dot ${dotColor}`}
          animate={{ opacity: [1, 0.3, 1] }}
          transition={{
            duration: 1.5,
            repeat: Infinity,
            ease: 'easeInOut',
          }}
        />
      )}
      <span className={`${textColor} rec-timer-value`}>
        {formatRecordingTime(time)}
      </span>
    </div>
  );
}
