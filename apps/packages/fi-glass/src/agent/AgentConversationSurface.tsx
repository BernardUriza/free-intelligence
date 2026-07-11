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
 * Pure orchestrator (REGION-PROPS-1): the regions receive the surface's whole
 * props object as `surface` and read their own slice + copy defaults — the
 * orchestrator never re-threads passthroughs. It owns only the shared state
 * (input, dictation, focus, append) and hands each region what IT derives:
 * the conversation slice, the composing state, the layout inset.
 */

import { useState } from 'react';
import { useTouchTargetStyle } from '../shell/touchTarget';
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
} from './conversation-surface/types';

export function AgentConversationSurface(props: AgentConversationSurfaceProps) {
  const {
    conversation,
    layout = 'viewport',
    voiceAdapter,
    onVoiceError,
    composerAppend,
    onComposerAppendConsumed,
  } = props;
  const { messages, turn, author, isStreaming, turnError, send, stop, retry, dismissError, newConversation } =
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

  const onSend = () => {
    const t = input.trim();
    if (!t) return;
    setInput('');
    send(t);
  };

  return (
    <div style={rootStyle}>
      <TranscriptRegion
        surface={props}
        conversation={{ messages, turn, author, isStreaming, turnError, retry, dismissError }}
        contentInset={contentInset}
      />
      <ComposerRegion
        surface={props}
        state={{
          input,
          setInput,
          onSend,
          canSend: input.trim().length > 0 && !isStreaming,
          inputRef,
          dictation,
          isStreaming,
          onStop: stop,
          hasThread: messages.length > 0 || isStreaming,
          newConversation,
        }}
        contentInset={contentInset}
      />
    </div>
  );
}
