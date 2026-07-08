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
 * Pure orchestrator: the props contract, hooks and sub-components live in
 * ./conversation-surface (types, focus recovery, dictation wiring, external
 * composer append, transcript, error banner, new-chat CTA, composer controls).
 */

import { useState, type CSSProperties } from 'react';
import { useStickToBottom } from 'use-stick-to-bottom';
import type { ChatMessage } from '@free-intelligence/core';
import { Composer, ComposerFrame } from '../composer';
import { ScrollToBottomButton } from './ScrollToBottomButton';
import { useMediaQuery } from '../shell/useMediaQuery';
import { useTouchTargetStyle } from '../shell/touchTarget';
import type { AgentConversationSurfaceProps } from './conversation-surface/types';
import {
  useComposerFocus,
  useSurfaceDictation,
  useComposerAppend,
} from './conversation-surface/hooks';
import {
  TranscriptMessages,
  TurnErrorBanner,
  NewChatButton,
  ComposerControls,
} from './conversation-surface/components';

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

  // B3-FIGLASS-MOBILE-1 — the fluid center cap is a desktop affordance; on a
  // phone the fixed 60px inset starves the composer (textarea < 300px at 390),
  // so the inset collapses to a thin gutter below the mobile breakpoint.
  const isMobileViewport = useMediaQuery('(max-width: 768px)');
  const contentInset = isMobileViewport ? 'calc(100% - 16px)' : 'calc(100% - 60px)';

  // B3-FIGLASS-12 — pin-to-bottom. The hook is called unconditionally (hooks
  // rule); when autoScroll is off the refs simply never attach, so it observes
  // nothing. isAtBottom starts true → no phantom button on first paint/SSR.
  const stick = useStickToBottom({ initial: 'instant', resize: 'smooth' });

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

  // FG-2: the root sizes itself per `layout`. "viewport" keeps the full-page
  // 100dvh (backward-compatible default); "contained" fills its parent cell and
  // clips at the root so the transcript region scrolls internally, never the page.
  const rootStyle: CSSProperties =
    layout === 'contained'
      ? { display: 'flex', flexDirection: 'column', height: '100%', minHeight: 0, overflow: 'hidden' }
      : { display: 'flex', flexDirection: 'column', height: '100dvh' };

  return (
    // B3-FIGLASS-15: the ROOT is full-width — the fluid cap (100% minus a 60px
    // gutter) lives on INNER content wrappers (transcript + composer), never on
    // the scroll container, so the scrollbar renders at the viewport edge like
    // ChatGPT/AURITY /chat instead of glued to the centered column.
    <div style={rootStyle}>
      {/* Relative anchor: hosts the scroll area + the floating jump-to-latest
          button, so the button stays glued to the transcript's bottom edge. */}
      <div style={{ position: 'relative', flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column' }}>
        <div
          ref={autoScroll ? stick.scrollRef : undefined}
          style={{ flex: 1, overflowY: 'auto', padding: '1.25rem 1rem' }}
        >
          <div
            ref={autoScroll ? stick.contentRef : undefined}
            style={{ maxWidth: contentInset, margin: '0 auto', width: '100%' }}
          >
            {idle ? (
              emptyState
            ) : (
              <TranscriptMessages
                messages={messages}
                turn={turn}
                isStreaming={isStreaming}
                showPersistedTrace={showPersistedTrace}
                agentPanelProps={agentPanelProps}
                showCopyAction={showCopyAction}
                renderHeader={renderHeader}
                renderBadge={renderBadge}
                renderActions={renderActions}
                resolveBubbleClass={resolveBubbleClass}
                collapseUserMessages={collapseUserMessages}
                collapseMaxHeight={collapseMaxHeight}
                showMoreLabel={showMoreLabel}
                showLessLabel={showLessLabel}
                collapseToggleClassName={collapseToggleClassName}
              />
            )}

            {/* B3-FIGLASS-8: recoverable failure. The watchdog/error already dropped
                us out of streaming, so this replaces the zombie "thinking…" panel. */}
            {turnError && (
              <TurnErrorBanner
                error={turnError}
                onRetry={retry}
                onDismiss={dismissError}
                className={errorClassName}
                retryLabel={retryLabel}
                dismissLabel={dismissLabel}
                retryButtonClassName={retryButtonClassName}
                dismissButtonClassName={dismissButtonClassName}
              />
            )}
          </div>
        </div>
        {/* Floating jump-to-latest: only when pinning is on and the user has
            scrolled away from the bottom (use-stick-to-bottom's isAtBottom). */}
        {autoScroll && !stick.isAtBottom && (
          <ScrollToBottomButton
            onClick={() => void stick.scrollToBottom()}
            label={scrollToBottomLabel}
            className={scrollToBottomClassName}
            iconClassName={scrollToBottomIconClassName}
          />
        )}
      </div>

      <div style={{ padding: '0.75rem 1rem 1.25rem', borderTop: '1px solid rgba(255,255,255,0.06)' }}>
        {/* Composer column shares the transcript's fluid center cap (the
            section itself spans full width so its top border does too). */}
        <div style={{ maxWidth: contentInset, margin: '0 auto', width: '100%', containerType: 'inline-size', containerName: 'fi-composer' }}>
          {hasThread && showNewChatButton && (
            <NewChatButton onClick={newConversation} disabled={isStreaming} label={newChatLabel} />
          )}
          {aboveComposer && (
            <div className="fi-surface-above-composer" style={{ marginBottom: '0.5rem' }}>
              {aboveComposer}
            </div>
          )}
          {/* Floating composer box — ONE container wrapping the textarea row and
              the controls row, mirroring the shell's chat-input-floating-box
              (AURITY). The canary audit found mic/send floating OUTSIDE the
              frosted box as siblings; the box structure is framework-owned so
              every consumer inherits the corrected anatomy. COMPOSER-FRAME-1
              formalizes it as ComposerFrame (header/body/footer slots): the
              controls row is the footer slot; the header slot is where drafts
              and previews will land. */}
          <ComposerFrame
            className={composerBoxClassName}
            header={composerHeader}
            headerClassName={composerHeaderClassName}
            footerClassName={composerControlsClassName}
            footer={
              showSendButton || micSlotOverride != null || dictation.micAvailable ? (
                <ComposerControls
                  dictation={dictation}
                  micSlotOverride={micSlotOverride}
                  micSlotClassName={micSlotClassName}
                  micButtonClassName={micButtonClassName}
                  voiceVisualizerClassName={voiceVisualizerClassName}
                  voiceVisualizerBarClassName={voiceVisualizerBarClassName}
                  showSendButton={showSendButton}
                  canSend={canSend}
                  isStreaming={isStreaming}
                  onSend={onSend}
                  sendLabel={sendLabel}
                  sendButtonClassName={sendButtonClassName}
                  sendButtonIconClassName={sendButtonIconClassName}
                />
              ) : null
            }
          >
            <Composer
              message={input}
              loading={isStreaming}
              placeholder={composerPlaceholder}
              onMessageChange={setInput}
              onSend={onSend}
              areaClassName={composerAreaClassName}
              textareaClassName={composerTextareaClassName}
              // The input fills the composer area regardless of how the consumer
              // styles it (e.g. a flex area): growth is owned here, in the
              // framework, not patched in by a consumer reaching into `.relative`.
              wrapperStyle={{ flex: '1 1 0%', minWidth: 0 }}
              // Typed focus handle (B3-FIGLASS-10): the surface refocuses the
              // input after dictation/send/stream — no internal-DOM reach.
              textareaRef={inputRef}
            />
          </ComposerFrame>
        </div>
      </div>
    </div>
  );
}
