'use client';

/**
 * ChatMessageList - Re-export from modular architecture
 *
 * The full implementation is in ./message-list/
 *
 * Architecture:
 * - message-list/config/: Style configuration
 * - message-list/core/: Types and interfaces
 * - message-list/hooks/: Business logic
 * - message-list/ui/: Atomic components
 *
 * Design: Dense style (Claude.ai / ChatGPT inspired)
 * - No bubbles
 * - Minimal spacing
 * - Subtle avatars
 * - Hover actions only
 */

// Re-export main component
export { ChatMessageList, type ChatMessageListProps } from './message-list';

// Re-export sub-components for advanced usage
export {
  MessageAvatar,
  MessageMeta,
  MessageContent,
  MessageActions,
  ChatMessage,
  DateDivider,
  TypingIndicator,
} from './message-list';

// Re-export hooks
export { useMessageGroups } from './message-list';

// Re-export styles for customization
export { messageStyles, markdownStyles } from './message-list';
