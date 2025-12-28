'use client';

/**
 * DateDivider - Shows date separators between message groups
 *
 * Displays "Hoy", "Ayer", or formatted date between messages from different days.
 * SOLID: Single responsibility - only renders date dividers
 */

import { memo } from 'react';
import { motion } from 'framer-motion';
import type { DateDividerType } from '@aurity-standalone/hooks/useMessageGroups';

export interface DateDividerProps {
  label: string;
  type?: DateDividerType;
  showLines?: boolean;
  animate?: boolean;
}

const pillClasses: Record<DateDividerType, string> = {
  today: 'chat-date-pill-today',
  yesterday: 'chat-date-pill-yesterday',
  date: 'chat-date-pill-default',
};

export const DateDivider = memo(function DateDivider({
  label,
  type = 'date',
  showLines = true,
  animate = true,
}: DateDividerProps) {
  const content = (
    <div className="chat-date-divider">
      {showLines && <div className="chat-date-divider-line-left" />}
      <span className={pillClasses[type]}>{label}</span>
      {showLines && <div className="chat-date-divider-line-right" />}
    </div>
  );

  if (!animate) return content;

  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      {content}
    </motion.div>
  );
});

/**
 * DateDividerCompact - Compact variant for inline use
 */
export const DateDividerCompact = memo(function DateDividerCompact({
  label,
}: Pick<DateDividerProps, 'label'>) {
  return (
    <div className="chat-date-divider-compact">
      <span className="chat-date-pill-compact">{label}</span>
    </div>
  );
});
