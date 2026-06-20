// fi-glass · shell (Curio, element 96) — the chat shell.
// Orchestrator + presentational skeleton, dependency-inverted over core's
// ChatHook. Domain pieces (persona selector, history, messages) are slots the
// app fills; auth/navigation/voice/upload arrive as typed props.
// fi-glass NEVER imports useAuth / useFIConversation / usePersonas / next/* /
// @/components/ui/*.

export { ChatWidget } from './ChatWidget';
export { ChatSurface, type ChatSurfaceProps } from './ChatSurface';
export { ChatContent } from './ChatContent';
export { ChatWidgetContainer, type ChatWidgetContainerProps } from './ChatWidgetContainer';
export { ChatWidgetHeader, type ChatWidgetHeaderProps } from './ChatWidgetHeader';
export { ChatToolbar, type ChatToolbarProps } from './ChatToolbar';
export { ChatFilePreview, type ChatFilePreviewProps } from './ChatFilePreview';
export { ChatStartScreen, type ChatStartScreenProps } from './ChatStartScreen';
export { FloatingButton, type FloatingButtonProps } from './FloatingButton';

export {
  useChatWidgetState,
  type UseChatWidgetStateOptions,
  type UseChatWidgetStateReturn,
} from './useChatWidgetState';

export {
  useMediaQuery,
  useBreakpoints,
  clearMediaQueryCache,
  type UseMediaQueryOptions,
  type Breakpoints,
  type BreakpointMatches,
} from './useMediaQuery';

export {
  defaultChatConfig,
  defaultTheme,
  defaultBehavior,
  defaultTimestampConfig,
  defaultAnimationConfig,
  mergeChatConfig,
  CHAT_BREAKPOINTS,
  type ChatConfig,
  type ChatTheme,
  type ChatBehavior,
  type TimestampConfig,
  type AnimationConfig,
  type ChatBreakpoints,
} from './config';

export type {
  ChatWidgetProps,
  ChatContentProps,
  ChatViewMode,
  ResponseMode,
  PersonaType,
  ChatNavDest,
  UploadStatus,
  VoiceRecordingState,
  ShellStreamingState,
} from './types';

export {
  FI_TOUCH_TARGET_CLASS,
  ensureTouchTargetStyle,
  useTouchTargetStyle,
  withTouchTarget,
} from './touchTarget';
