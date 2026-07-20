// fi-glass · shell — cross-surface primitives, NOT a chat orchestrator.
//
// This directory used to hold two unrelated things under one name: the legacy
// ChatWidget orchestrator (~1,300 LOC whose only consumer was aurity, and whose
// `ChatSurface` had no consumer at all), and a handful of primitives that every
// live surface actually depends on. The orchestrator moved to
// `apps/aurity/components/chat/glass-shell` — where its sole caller lives — and
// what remains here is only the shared part (B3-FIGLASS-SHELL-CONSOLIDATION-1):
//
//  - the touch-target minimum, composed by 10 controls across voice/, messages/,
//    composer/, agent/ and og118's own sidebar
//  - `useMediaQuery`, which the agentic workspace shell and surface layout read
//  - `ChatFilePreview` + the `UploadStatus` vocabulary og118 types its project
//    uploads against
//  - the shared type vocabulary (view mode, response mode, persona, nav dest)
//
// fi-glass NEVER imports useAuth / useFIConversation / usePersonas / next/* /
// @/components/ui/*.

export { ChatFilePreview, type ChatFilePreviewProps } from './ChatFilePreview';

export {
  useMediaQuery,
  useBreakpoints,
  clearMediaQueryCache,
  type UseMediaQueryOptions,
  type Breakpoints,
  type BreakpointMatches,
} from './useMediaQuery';

export {
  FI_TOUCH_TARGET_CLASS,
  ensureTouchTargetStyle,
  useTouchTargetStyle,
  withTouchTarget,
} from './touchTarget';

export type {
  ChatViewMode,
  ResponseMode,
  PersonaType,
  ChatNavDest,
  UploadStatus,
  VoiceRecordingState,
} from './types';
