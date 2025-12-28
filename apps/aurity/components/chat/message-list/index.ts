/**
 * Message List Module
 *
 * Modular architecture:
 * - config/: Style configuration
 * - core/: Types and interfaces
 * - hooks/: Business logic
 * - ui/: Atomic components
 */

// Main component
export { ChatMessageList, type ChatMessageListProps } from './ChatMessageList';

// UI components (for advanced usage)
export {
  MessageAvatar,
  MessageMeta,
  MessageContent,
  MessageActions,
  ChatMessage,
  DateDivider,
  TypingIndicator,
} from './ui';

// Hooks
export { useMessageGroups } from './hooks';

// Types
export type { BaseMessageProps, MessageGroup, ActionState } from './core';

// Styles (for customization)
export { messageStyles, markdownStyles } from './config';
