'use client';

/**
 * AgentConversationSurface — full-page agentic chat: a visible transcript above
 * the live glass-box turn, with an explicit "new conversation" control.
 *
 * This is the agentic twin of shell/ChatSurface: ChatSurface renders a ChatHook
 * (plain chat), this renders an AgentConversation (transcript + per-turn
 * glass-box). It is the framework home for DD-002 — the consumer used to
 * hand-roll this layout. Material-agnostic and app-neutral: no endpoint, token,
 * branding or backend. Apps inject those via slots (emptyState, aboveComposer)
 * and copy props.
 *
 * Pure orchestrator (REGION-PROPS-1): the orchestrator hands its props object
 * to each region as `surface` and never re-threads passthroughs. Each region
 * TYPES that object down to the capability slices it actually consumes
 * (`ComposerRegionSurface` / `TranscriptRegionSurface`), so the boundary is
 * enforced by the compiler instead of by convention — one object passed, a
 * narrow contract received. The orchestrator owns only the shared state
 * (input, images, dictation, focus, append) and hands each region what IT
 * derives: the conversation slice, the composing state, the layout inset.
 */

import { useEffect, useState } from 'react';
import { useTouchTargetStyle } from '../shell/touchTarget';
import { useComposerImages } from '../composer/useComposerImages';
import type { AgentConversationSurfaceProps } from './conversation-surface/types';
import {
  useComposerFocus,
  useSurfaceDictation,
  useComposerAppend,
  useSurfaceLayout,
} from './conversation-surface/hooks';
import { TranscriptRegion, ComposerRegion } from './conversation-surface/components';

export type {
  AgentConversationSurfaceProps,
  AgentConversationSurfaceLayout,
  // B3-FIGLASS-SURFACE-PROPS-1: the cohesive capability slices the god-props
  // interface was decomposed into — each reusable/typeable on its own.
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
  // B3-FIGLASS-SURFACE-PROPS-2: the per-region unions the slices compose into.
  ComposerRegionSurface,
  TranscriptRegionSurface,
} from './conversation-surface/types';

export function AgentConversationSurface(props: AgentConversationSurfaceProps) {
  const {
    conversation,
    layout = 'viewport',
    voiceAdapter,
    onVoiceError,
    composerAppend,
    onComposerAppendConsumed,
    imageAttachments = false,
    maxAttachedImages,
    onImageAttachmentError,
  } = props;
  const {
    messages,
    turn,
    author,
    isStreaming,
    turnError,
    persistError,
    retryPersist,
    dismissPersistError,
    send,
    stop,
    retry,
    dismissError,
    newConversation,
    unsentText,
    unsentImages,
    clearUnsent,
  } =
    conversation;
  const [input, setInput] = useState('');

  // B3-FIGLASS-MOBILE-2 — guarantee the touch-target stylesheet is present so the
  // composed send button (and any other fi-glass control on the surface) gets its
  // 44×44 mobile minimum even if no other control mounted it first.
  useTouchTargetStyle();

  const { rootStyle, contentInset } = useSurfaceLayout(layout);
  useComposerAppend({ composerAppend, onComposerAppendConsumed, setInput });
  const dictation = useSurfaceDictation({ voiceAdapter, input, setInput, onVoiceError });
  const inputRef = useComposerFocus({
    isStreaming,
    isTranscribing: dictation.isTranscribing,
  });
  // OG118-IMAGE-UPLOAD-1: the surface owns the attachment state (like it owns
  // the input string); the switch only gates the UI, so an app that never
  // enables it renders byte-identically to before.
  const images = useComposerImages({
    maxImages: maxAttachedImages,
    onError: onImageAttachmentError,
  });
  const restoreImages = images.restore;

  // A failed turn hands back what the user wrote (the watchdog used to revert it
  // out of the thread and destroy it). Put it back in the box — the framework
  // does it, so no consumer can forget and cost the user their prompt. An input
  // the user has since typed into wins: never clobber live typing.
  //
  // The IMAGES come back too: the send cleared the drafts optimistically, so
  // restoring only the text would return a prompt whose pictures are silently
  // missing — the user re-sends and the attachment never existed.
  useEffect(() => {
    if (!unsentText && !unsentImages) return;
    if (unsentText) setInput((current) => (current.trim() ? current : unsentText));
    if (imageAttachments && unsentImages && unsentImages.length > 0) {
      restoreImages(unsentImages);
    }
    clearUnsent();
  }, [unsentText, unsentImages, imageAttachments, restoreImages, clearUnsent]);

  const onSend = () => {
    const t = input.trim();
    const attached = imageAttachments ? images.toMessageImages() : [];
    if (!t && attached.length === 0) return;
    setInput('');
    images.clear();
    send(t, attached.length > 0 ? attached : undefined);
  };

  return (
    <div style={rootStyle}>
      <TranscriptRegion
        surface={props}
        conversation={{
          messages,
          turn,
          author,
          isStreaming,
          turnError,
          retry,
          dismissError,
          persistError,
          retryPersist,
          dismissPersistError,
        }}
        contentInset={contentInset}
      />
      <ComposerRegion
        surface={props}
        state={{
          input,
          setInput,
          onSend,
          canSend:
            (input.trim().length > 0 || (imageAttachments && images.drafts.length > 0)) &&
            !isStreaming,
          inputRef,
          dictation,
          isStreaming,
          onStop: stop,
          hasThread: messages.length > 0 || isStreaming,
          newConversation,
          images: imageAttachments ? images : null,
        }}
        contentInset={contentInset}
      />
    </div>
  );
}
