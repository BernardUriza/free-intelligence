/**
 * Unified Message Types
 * Shared interfaces for all message variants (Chat, Onboarding, TV)
 */

import type { FIMessage } from '@aurity-standalone/types/assistant';
import type { LucideIcon } from 'lucide-react';

// Re-export FIMessage for convenience
export type { FIMessage };

/**
 * Persona visual styling configuration
 */
export interface PersonaStyle {
  border: string;
  bg: string;
  glow: string;
  Icon: LucideIcon;
  labelColor: string;
}

/**
 * Base props shared by all message variants
 */
export interface BaseMessageProps {
  /** The message to display */
  message: FIMessage;
  /** Additional CSS classes */
  className?: string;
}

/**
 * Props for ChatMessage variant (full-featured)
 */
export interface ChatMessageProps extends BaseMessageProps {
  /** Is the message currently streaming */
  isStreaming?: boolean;
  /** Show thinking/reasoning block */
  showThinking?: boolean;
}

/**
 * Props for OnboardingMessage variant (with markdown + actions)
 */
export interface OnboardingMessageProps extends BaseMessageProps {
  /** Show timestamp */
  showTimestamp?: boolean;
  /** Show sender name */
  showSenderName?: boolean;
  /** Animate entrance */
  animate?: boolean;
  /** Override border radius */
  borderRadiusOverride?: string;
}

/**
 * Props for TVMessage variant (simple, large text)
 */
export interface TVMessageProps extends BaseMessageProps {
  /** Override font size calculation */
  fontSize?: string;
}

/**
 * Hook options for useMessage
 */
export interface UseMessageOptions {
  message: FIMessage;
  persona?: string;
}

/**
 * Return type for useMessage hook
 */
export interface UseMessageReturn {
  // Derived state
  isUser: boolean;
  displayName: string;
  personaStyle: PersonaStyle;
  personaLabel: string;
  persona: string;

  // Actions
  copyToClipboard: () => Promise<void>;
}
