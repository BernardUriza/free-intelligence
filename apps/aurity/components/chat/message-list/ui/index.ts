/**
 * Message List UI Components
 *
 * Re-exports unified primitives from ui/message for backwards compatibility.
 * Only DateDivider and TypingIndicator are chat-specific.
 */

// Re-export from unified message system (single source of truth)
export {
  MessageAvatar,
  MessageMeta,
  MessageContent,
  MessageActions,
  type MessageAvatarProps,
  type MessageMetaProps,
  type MessageContentProps,
  type MessageActionsProps,
} from '@/components/ui/message/primitives';

// Chat-specific components (not in unified system)
export { DateDivider, type DateDividerProps } from './DateDivider';
export { TypingIndicator } from './TypingIndicator';
