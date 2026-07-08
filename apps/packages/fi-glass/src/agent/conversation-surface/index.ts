/**
 * fi-glass · conversation-surface — the internal organs of
 * AgentConversationSurface, split by responsibility:
 *  - types.ts: the public props contract (re-exported by the surface)
 *  - persistedTraceTurn.ts: persisted trace → renderable AgentTurnState
 *  - hooks/: focus recovery, dictation wiring, external composer append
 *  - components/: transcript, error banner, new-chat CTA, composer controls
 *
 * Internal module: apps import from `fi-glass/agent`, never from here.
 */

export type { AgentConversationSurfaceProps, AgentConversationSurfaceLayout } from './types';
export { persistedTraceTurn } from './persistedTraceTurn';
export { useComposerFocus, useSurfaceDictation, useComposerAppend, type SurfaceDictation } from './hooks';
export {
  TranscriptMessages,
  TurnErrorBanner,
  NewChatButton,
  ComposerControls,
  type TranscriptMessagesProps,
  type TurnErrorBannerProps,
  type NewChatButtonProps,
  type ComposerControlsProps,
} from './components';
