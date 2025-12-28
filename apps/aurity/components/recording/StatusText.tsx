/**
 * StatusText - Recording Status Display Component
 *
 * Shows current recording status with optional loader.
 * Used by: RecordingControls, VoiceMicButton
 */

'use client';

import { Loader2 } from 'lucide-react';
import { motion } from 'framer-motion';

export interface StatusTextProps {
  /** Status message to display */
  text: string;
  /** Text color (Tailwind class) */
  color?: string;
  /** Show loading spinner */
  showLoader?: boolean;
  /** Animate with pulse effect */
  animate?: boolean;
  /** Additional classes */
  className?: string;
}

export function StatusText({
  text,
  color = 'text-slate-400',
  showLoader = false,
  animate = false,
  className = '',
}: StatusTextProps) {
  const content = (
    <div className={`flex items-center justify-center gap-2 ${color} ${className}`}>
      {showLoader && <Loader2 className="h-5 w-5 animate-spin" />}
      <p className="font-medium">{text}</p>
    </div>
  );

  if (animate) {
    return (
      <motion.div
        initial={{ opacity: 0.7 }}
        animate={{ opacity: [0.7, 1, 0.7] }}
        transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut' }}
      >
        {content}
      </motion.div>
    );
  }

  return content;
}
