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

// Primitives (to be added when migrating from chat/message-list/ui/)
// export { MessageAvatar } from './primitives/MessageAvatar';
// export { MessageMeta } from './primitives/MessageMeta';
// export { MessageContent } from './primitives/MessageContent';
// export { MessageActions } from './primitives/MessageActions';
