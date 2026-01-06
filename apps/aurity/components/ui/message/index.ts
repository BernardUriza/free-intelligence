/**
 * Unified Message System
 *
 * Headless component pattern with multiple variants:
 * - TVMessage: Large text for TV displays (WaitingRoomHost)
 * - ChatMessage: Full-featured for chat widget (coming soon)
 * - OnboardingMessage: Markdown + actions for onboarding (coming soon)
 *
 * @see https://martinfowler.com/articles/headless-component.html
 */

// Types
export type {
  FIMessage,
  PersonaStyle,
  BaseMessageProps,
  ChatMessageProps,
  OnboardingMessageProps,
  TVMessageProps,
  UseMessageOptions,
  UseMessageReturn,
} from './types';

// Hooks
export { useMessage, useMessageSimple } from './hooks/useMessage';

// Styles
export {
  PERSONA_STYLES,
  FALLBACK_STYLE,
  getPersonaStyle,
  generatePersonaLabel,
} from './styles/persona-styles';

export {
  messageStyles,
  markdownStyles,
  tvStyles,
  getTVFontSize,
} from './styles/message-styles';

// Variants
export { TVMessage } from './variants/TVMessage';
export { ChatMessage } from './variants/ChatMessage';
export { OnboardingMessage } from './variants/OnboardingMessage';

// Primitives
export {
  MessageAvatar,
  MessageMeta,
  MessageContent,
  MessageActions,
  type MessageAvatarProps,
  type MessageMetaProps,
  type MessageContentProps,
  type MessageActionsProps,
} from './primitives';
