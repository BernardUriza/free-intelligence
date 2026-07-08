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
 * Pure orchestrator: the props contract, hooks and regions live in
 * ./conversation-surface — useSurfaceLayout (root sizing + fluid cap),
 * dictation/focus/append wiring, TranscriptRegion (scroll + messages + error +
 * jump-to-latest) and ComposerRegion (new-chat CTA + slots + ComposerFrame).
 * This file owns only the shared state (input, dictation) and the derivations
 * both regions read (idle, hasThread, canSend).
 */

import { useState } from 'react';
import type { ChatMessage } from '@free-intelligence/core';
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

export function AgentConversationSurface({
  conversation,
  layout = 'viewport',
  composerPlaceholder,
  newChatLabel = 'New chat',
  showNewChatButton = true,
  emptyState,
  aboveComposer,
  composerHeader,
  composerHeaderClassName,
  agentPanelProps,
  showPersistedTrace = true,
  composerBoxClassName,
  composerAreaClassName,
  composerTextareaClassName,
  composerControlsClassName,
  showCopyAction = false,
  renderHeader,
  renderBadge,
  renderActions,
  messageBubbleClassName,
  voiceAdapter,
  micSlotClassName,
  micButtonClassName,
  onVoiceError,
  voiceVisualizerClassName,
  voiceVisualizerBarClassName,
  showSendButton = true,
  sendButtonClassName,
  sendButtonIconClassName,
  sendLabel = 'Enviar mensaje',
  composerAppend,
  onComposerAppendConsumed,
  micSlotOverride,
  errorClassName,
  retryLabel = 'Reintentar',
  dismissLabel = 'Descartar',
  retryButtonClassName,
  dismissButtonClassName,
  autoScroll = true,
  scrollToBottomLabel = 'Ir al final',
  scrollToBottomClassName,
  scrollToBottomIconClassName,
  collapseUserMessages = true,
  collapseMaxHeight,
  showMoreLabel,
  showLessLabel,
  collapseToggleClassName,
}: AgentConversationSurfaceProps) {
  const { messages, turn, isStreaming, turnError, send, retry, dismissError, newConversation } =
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

  // Resolve the per-bubble class. A string applies to every role (legacy); a
  // function lets the consumer vary it per message/role. Returning undefined
  // (e.g. for an unknown role) yields no extra class — never throws.
  const resolveBubbleClass = (message: ChatMessage): string | undefined =>
    typeof messageBubbleClassName === 'function'
      ? messageBubbleClassName(message)
      : messageBubbleClassName;

  // Empty thread + nothing in flight → show the app's start screen.
  const idle =
    messages.length === 0 &&
    !isStreaming &&
    turn.status === 'thinking' &&
    !turn.plan &&
    turn.steps.length === 0 &&
    !turn.text;
  const hasThread = messages.length > 0 || isStreaming;

  const onSend = () => {
    const t = input.trim();
    if (!t) return;
    setInput('');
    send(t);
  };
  const canSend = input.trim().length > 0 && !isStreaming;

  return (
    <div style={rootStyle}>
      <TranscriptRegion
        conversation={{ messages, turn, isStreaming, turnError, retry, dismissError }}
        idle={idle}
        autoScroll={autoScroll}
        contentInset={contentInset}
        resolveBubbleClass={resolveBubbleClass}
        emptyState={emptyState}
        showPersistedTrace={showPersistedTrace}
        agentPanelProps={agentPanelProps}
        showCopyAction={showCopyAction}
        renderHeader={renderHeader}
        renderBadge={renderBadge}
        renderActions={renderActions}
        collapseUserMessages={collapseUserMessages}
        collapseMaxHeight={collapseMaxHeight}
        showMoreLabel={showMoreLabel}
        showLessLabel={showLessLabel}
        collapseToggleClassName={collapseToggleClassName}
        errorClassName={errorClassName}
        retryLabel={retryLabel}
        dismissLabel={dismissLabel}
        retryButtonClassName={retryButtonClassName}
        dismissButtonClassName={dismissButtonClassName}
        scrollToBottomLabel={scrollToBottomLabel}
        scrollToBottomClassName={scrollToBottomClassName}
        scrollToBottomIconClassName={scrollToBottomIconClassName}
      />
      <ComposerRegion
        contentInset={contentInset}
        hasThread={hasThread}
        isStreaming={isStreaming}
        newConversation={newConversation}
        dictation={dictation}
        input={input}
        setInput={setInput}
        onSend={onSend}
        canSend={canSend}
        inputRef={inputRef}
        showNewChatButton={showNewChatButton}
        newChatLabel={newChatLabel}
        showSendButton={showSendButton}
        sendLabel={sendLabel}
        aboveComposer={aboveComposer}
        composerHeader={composerHeader}
        composerHeaderClassName={composerHeaderClassName}
        composerBoxClassName={composerBoxClassName}
        composerAreaClassName={composerAreaClassName}
        composerTextareaClassName={composerTextareaClassName}
        composerControlsClassName={composerControlsClassName}
        composerPlaceholder={composerPlaceholder}
        micSlotOverride={micSlotOverride}
        micSlotClassName={micSlotClassName}
        micButtonClassName={micButtonClassName}
        voiceVisualizerClassName={voiceVisualizerClassName}
        voiceVisualizerBarClassName={voiceVisualizerBarClassName}
        sendButtonClassName={sendButtonClassName}
        sendButtonIconClassName={sendButtonIconClassName}
      />
    </div>
  );
}
