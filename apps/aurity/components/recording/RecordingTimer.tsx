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
  /** Text color (Tailwind class) */
  textColor?: string;
  /** Dot color (Tailwind class) */
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
  sm: 'text-sm',
  md: 'text-lg',
  lg: 'text-3xl',
};

export function RecordingTimer({
  time,
  visible = true,
  size = 'md',
  showDot = false,
  textColor = 'text-white',
  dotColor = 'bg-red-500',
  className = '',
}: RecordingTimerProps) {
  if (!visible || time <= 0) return null;

  return (
    <div className={`flex items-center gap-2 font-mono ${SIZE_CLASSES[size]} ${className}`}>
      {showDot && (
        <motion.div
          className={`w-2 h-2 rounded-full ${dotColor}`}
          animate={{ opacity: [1, 0.3, 1] }}
          transition={{
            duration: 1.5,
            repeat: Infinity,
            ease: 'easeInOut',
          }}
        />
      )}
      <span className={`${textColor} font-semibold`}>
        {formatRecordingTime(time)}
      </span>
    </div>
  );
}
