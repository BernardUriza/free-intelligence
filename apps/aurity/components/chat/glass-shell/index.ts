/**
 * aurity · glass-shell — the legacy ChatWidget orchestrator, relocated here from
 * `fi-glass/src/shell` (B3-FIGLASS-SHELL-CONSOLIDATION-1).
 *
 * WHY IT MOVED: it was never framework code. og118 — the app that actually ships
 * — renders the agentic surface (`fi-glass/agent`) and consumed exactly ZERO of
 * these components; `ChatSurface` had no consumer anywhere at all. aurity was the
 * sole caller, so the framework was carrying ~1,300 LOC of one app's UI. It now
 * lives with its only consumer.
 *
 * What stayed in `fi-glass/shell` is what more than one surface really shares:
 * the touch-target primitive, `useMediaQuery`, `ChatFilePreview` and the type
 * vocabulary og118 speaks.
 */

export { ChatWidget } from './ChatWidget';
export { ChatSurface, type ChatSurfaceProps } from './ChatSurface';
export { ChatContent } from './ChatContent';
export { ChatWidgetContainer } from './ChatWidgetContainer';
export { ChatWidgetHeader } from './ChatWidgetHeader';
export { ChatToolbar } from './ChatToolbar';
export { ChatStartScreen } from './ChatStartScreen';
export { FloatingButton } from './FloatingButton';
export {
  useChatWidgetState,
  type UseChatWidgetStateOptions,
  type UseChatWidgetStateReturn,
} from './useChatWidgetState';
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
export type { ChatWidgetProps, ChatContentProps, ShellStreamingState } from './types';
