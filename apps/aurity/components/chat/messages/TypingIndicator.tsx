'use client';

/**
 * TypingIndicator - Animated typing dots (like Slack/iMessage)
 *
 * Shows bouncing ellipsis to indicate the assistant is typing.
 * Uses semantic CSS classes with Framer Motion for animation.
 */

import { memo } from 'react';
import { motion } from 'framer-motion';

export interface TypingIndicatorProps {
  isTyping: boolean;
  ariaLabel?: string;
  dotColor?: string;
  size?: 'sm' | 'md' | 'lg';
}

const containerVariants = {
  initial: { opacity: 0, scale: 0.8 },
  animate: { opacity: 1, scale: 1, transition: { duration: 0.2 } },
  exit: { opacity: 0, scale: 0.8, transition: { duration: 0.15 } },
};

const containerClasses = {
  sm: 'chat-typing-container-sm',
  md: 'chat-typing-container-md',
  lg: 'chat-typing-container-lg',
};

const dotClasses = {
  sm: 'chat-typing-dot-sm',
  md: 'chat-typing-dot-md',
  lg: 'chat-typing-dot-lg',
};

export const TypingIndicator = memo(function TypingIndicator({
  isTyping,
  ariaLabel = 'El asistente está escribiendo...',
  dotColor = 'bg-purple-400',
  size = 'md',
}: TypingIndicatorProps) {
  if (!isTyping) return null;

  return (
    <motion.div
      variants={containerVariants}
      initial="initial"
      animate="animate"
      exit="exit"
      className={containerClasses[size]}
      role="status"
      aria-label={ariaLabel}
    >
      <span className="sr-only">{ariaLabel}</span>
      {[0, 1, 2].map((i) => (
        <motion.span
          key={i}
          initial={{ y: 0 }}
          animate={{ y: [-2, 2, -2] }}
          transition={{
            duration: 0.6,
            repeat: Infinity,
            repeatType: 'loop',
            delay: i * 0.15,
            ease: 'easeInOut',
          }}
          className={`${dotClasses[size]} ${dotColor}`}
        />
      ))}
    </motion.div>
  );
});

/**
 * TypingIndicatorPulse - More subtle pulse variant
 */
export const TypingIndicatorPulse = memo(function TypingIndicatorPulse({
  isTyping,
  ariaLabel = 'El asistente está escribiendo...',
}: Pick<TypingIndicatorProps, 'isTyping' | 'ariaLabel'>) {
  if (!isTyping) return null;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="chat-typing-pulse"
      role="status"
      aria-label={ariaLabel}
    >
      <motion.div
        animate={{ scale: [1, 1.2, 1], opacity: [0.5, 1, 0.5] }}
        transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut' }}
        className="chat-typing-pulse-dot"
      />
      <span>FI está pensando...</span>
    </motion.div>
  );
});
