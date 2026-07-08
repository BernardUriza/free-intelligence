'use client';

/**
 * fi-glass · conversation-surface/TranscriptRegion — the scrollable top half of
 * the surface: pin-to-bottom scroll container (B3-FIGLASS-12), fluid center cap
 * on the INNER wrapper (B3-FIGLASS-15: the scrollbar stays at the viewport
 * edge), the empty-state / transcript switch, the recoverable turn-error
 * banner (B3-FIGLASS-8) and the floating jump-to-latest button. Owns the
 * use-stick-to-bottom instance outright — no scroll state leaks up to the
 * orchestrator.
 */

import { useStickToBottom } from 'use-stick-to-bottom';
import type { ChatMessage } from '@free-intelligence/core';
import { ScrollToBottomButton } from '../../../ScrollToBottomButton';
import type { AgentConversation } from '../../../useAgentConversation';
import type { AgentConversationSurfaceProps } from '../../types';
import { TranscriptMessages } from './TranscriptMessages';
import { TurnErrorBanner } from './TurnErrorBanner';

export interface TranscriptRegionProps
  extends Pick<
    AgentConversationSurfaceProps,
    | 'emptyState'
    | 'agentPanelProps'
    | 'renderHeader'
    | 'renderBadge'
    | 'renderActions'
    | 'collapseMaxHeight'
    | 'showMoreLabel'
    | 'showLessLabel'
    | 'collapseToggleClassName'
    | 'errorClassName'
    | 'retryButtonClassName'
    | 'dismissButtonClassName'
    | 'scrollToBottomClassName'
    | 'scrollToBottomIconClassName'
  > {
  conversation: Pick<
    AgentConversation,
    'messages' | 'turn' | 'isStreaming' | 'turnError' | 'retry' | 'dismissError'
  >;
  /** True when the thread is empty and idle → render the app's start screen. */
  idle: boolean;
  autoScroll: boolean;
  /** The fluid center cap (100% minus the responsive gutter). */
  contentInset: string;
  resolveBubbleClass: (message: ChatMessage) => string | undefined;
  // Defaults resolved by the orchestrator → required here.
  showPersistedTrace: boolean;
  showCopyAction: boolean;
  collapseUserMessages: boolean;
  retryLabel: string;
  dismissLabel: string;
  scrollToBottomLabel: string;
}

export function TranscriptRegion({
  conversation,
  idle,
  autoScroll,
  contentInset,
  resolveBubbleClass,
  emptyState,
  showPersistedTrace,
  agentPanelProps,
  showCopyAction,
  renderHeader,
  renderBadge,
  renderActions,
  collapseUserMessages,
  collapseMaxHeight,
  showMoreLabel,
  showLessLabel,
  collapseToggleClassName,
  errorClassName,
  retryLabel,
  dismissLabel,
  retryButtonClassName,
  dismissButtonClassName,
  scrollToBottomLabel,
  scrollToBottomClassName,
  scrollToBottomIconClassName,
}: TranscriptRegionProps) {
  const { messages, turn, isStreaming, turnError, retry, dismissError } = conversation;

  // B3-FIGLASS-12 — pin-to-bottom. The hook is called unconditionally (hooks
  // rule); when autoScroll is off the refs simply never attach, so it observes
  // nothing. isAtBottom starts true → no phantom button on first paint/SSR.
  const stick = useStickToBottom({ initial: 'instant', resize: 'smooth' });

  return (
    // Relative anchor: hosts the scroll area + the floating jump-to-latest
    // button, so the button stays glued to the transcript's bottom edge.
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
  );
}
