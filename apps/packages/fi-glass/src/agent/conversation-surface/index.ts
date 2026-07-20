/**
 * fi-glass · conversation-surface — the internal organs of
 * AgentConversationSurface, split by responsibility:
 *  - types.ts: the public props contract (re-exported by the surface)
 *  - persistedTraceTurn.ts: persisted trace → renderable AgentTurnState
 *  - hooks/: focus recovery, dictation wiring, external composer append,
 *    surface layout (root sizing + fluid center cap)
 *  - components/transcript/: the scroll region (pin-to-bottom, messages,
 *    error banner, jump-to-latest)
 *  - components/composer/: the bottom section (new-chat CTA, aboveComposer
 *    slot, ComposerFrame + controls)
 *
 * Internal module: apps import from `fi-glass/agent`, never from here.
 */

export type {
  AgentConversationSurfaceProps,
  AgentConversationSurfaceLayout,
  SurfaceLayoutProps,
  SurfaceSlotProps,
  NewConversationProps,
  SurfaceComposerProps,
  SendControlProps,
  MessageRenderProps,
  DictationProps,
  ImageAttachmentProps,
  TurnErrorProps,
  AutoScrollProps,
  CollapseProps,
  ComposerRegionSurface,
  TranscriptRegionSurface,
} from './types';
export { persistedTraceTurn } from './persistedTraceTurn';
export {
  useComposerFocus,
  useSurfaceDictation,
  useComposerAppend,
  useSurfaceLayout,
  type SurfaceDictation,
  type SurfaceLayout,
} from './hooks';
export {
  TranscriptRegion,
  TranscriptMessages,
  TurnErrorBanner,
  ComposerRegion,
  ComposerControls,
  NewChatButton,
  type TranscriptRegionProps,
  type TranscriptMessagesProps,
  type TurnErrorBannerProps,
  type ComposerRegionProps,
  type ComposerControlsProps,
  type NewChatButtonProps,
} from './components';
