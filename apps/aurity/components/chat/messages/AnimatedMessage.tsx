'use client';

/**
 * AnimatedMessage - Wrapper for message animations
 *
 * Animations:
 * - Enter: Slide up + fade in (like iMessage)
 * - Exit: Fade out
 * - Sending: Subtle pulse
 * - Failed: Shake
 *
 * References:
 * - https://github.com/iarmankhan/animated-chat
 * - https://codesandbox.io/s/chat-message-animations-framer-motion-e4gs3l
 */

import { memo, type ReactNode } from 'react';
import { motion, AnimatePresence, type Variants } from 'framer-motion';
import type { MessageStatus } from '@aurity-standalone/hooks/useOptimisticMessages';

export interface AnimatedMessageProps {
  /** Unique key for animation */
  messageId: string;
  /** Message content */
  children: ReactNode;
  /** Is this a user message (right side) */
  isUser?: boolean;
  /** Message status for status-specific animations */
  status?: MessageStatus;
  /** Animation variant */
  variant?: 'default' | 'minimal' | 'none';
  /** Custom delay (for staggered animations) */
  delay?: number;
}

// ============================================================================
// ANIMATION VARIANTS
// ============================================================================

const messageVariants: Variants = {
  // Initial state (before entering)
  initial: (isUser: boolean) => ({
    opacity: 0,
    y: 20,
    x: isUser ? 20 : -20,
    scale: 0.95,
  }),

  // Visible state
  animate: {
    opacity: 1,
    y: 0,
    x: 0,
    scale: 1,
    transition: {
      type: 'spring',
      stiffness: 500,
      damping: 30,
      mass: 1,
    },
  },

  // Exit state
  exit: {
    opacity: 0,
    scale: 0.95,
    transition: {
      duration: 0.15,
    },
  },
};

// Sending state - subtle pulse
const sendingVariants: Variants = {
  animate: {
    opacity: [0.7, 1, 0.7],
    transition: {
      duration: 1.5,
      repeat: Infinity,
      ease: 'easeInOut',
    },
  },
};

// Failed state - shake
const failedVariants: Variants = {
  animate: {
    x: [0, -5, 5, -5, 5, 0],
    transition: {
      duration: 0.4,
      ease: 'easeInOut',
    },
  },
};

// Minimal variant (just fade)
const minimalVariants: Variants = {
  initial: { opacity: 0 },
  animate: {
    opacity: 1,
    transition: { duration: 0.2 },
  },
  exit: {
    opacity: 0,
    transition: { duration: 0.1 },
  },
};

// ============================================================================
// COMPONENT
// ============================================================================

export const AnimatedMessage = memo(function AnimatedMessage({
  messageId,
  children,
  isUser = false,
  status = 'sent',
  variant = 'default',
  delay = 0,
}: AnimatedMessageProps) {
  // No animation variant
  if (variant === 'none') {
    return <>{children}</>;
  }

  // Minimal variant
  if (variant === 'minimal') {
    return (
      <motion.div
        key={messageId}
        variants={minimalVariants}
        initial="initial"
        animate="animate"
        exit="exit"
      >
        {children}
      </motion.div>
    );
  }

  // Default variant with status-specific animations
  return (
    <motion.div
      key={messageId}
      custom={isUser}
      variants={messageVariants}
      initial="initial"
      animate="animate"
      exit="exit"
      transition={{ delay }}
      layout // Smooth reflow when messages are added/removed
    >
      {/* Status-specific animation wrapper */}
      {status === 'sending' ? (
        <motion.div variants={sendingVariants} animate="animate">
          {children}
        </motion.div>
      ) : status === 'failed' ? (
        <motion.div variants={failedVariants} animate="animate">
          {children}
        </motion.div>
      ) : (
        children
      )}
    </motion.div>
  );
});

// ============================================================================
// ANIMATED LIST WRAPPER
// ============================================================================

export interface AnimatedMessageListProps {
  children: ReactNode;
}

export const AnimatedMessageList = memo(function AnimatedMessageList({
  children,
}: AnimatedMessageListProps) {
  return <AnimatePresence mode="popLayout">{children}</AnimatePresence>;
});
