'use client';

/**
 * fi-glass · conversation-surface/TranscriptRegion — the scrollable top half of
 * the surface: pin-to-bottom scroll container (B3-FIGLASS-12), fluid center cap
 * on the INNER wrapper (B3-FIGLASS-15: the scrollbar stays at the viewport
 * edge), the empty-state / transcript switch, the recoverable turn-error
 * banner (B3-FIGLASS-8) and the floating jump-to-latest button.
 *
 * Contract shape (REGION-PROPS-1, kills the 20-prop thread-through): the
 * region takes the surface's whole public props object as `surface` — it reads
 * its slice and resolves ITS copy defaults — plus the orchestrator-owned
 * conversation slice and the shared layout inset. Region-local derivations
 * (idle, per-bubble class resolution) live here, not upstairs; the
 * use-stick-to-bottom instance is owned outright — no scroll state leaks up.
 */

import { useStickToBottom } from 'use-stick-to-bottom';
import type { ChatMessage } from '@free-intelligence/core';
import { ScrollToBottomButton } from '../../../ScrollToBottomButton';
import type { AgentConversation } from '../../../useAgentConversation';
import type { AgentConversationSurfaceProps } from '../../types';
import { TranscriptMessages } from './TranscriptMessages';
import { TurnErrorBanner } from './TurnErrorBanner';

export interface TranscriptRegionProps {
  /** The surface's public props — the region reads its slice + copy defaults. */
  surface: AgentConversationSurfaceProps;
  /** The live conversation slice the transcript renders. */
  conversation: Pick<
    AgentConversation,
    | 'messages'
    | 'turn'
    | 'author'
    | 'isStreaming'
    | 'turnError'
    | 'retry'
    | 'dismissError'
    | 'persistError'
    | 'retryPersist'
    | 'dismissPersistError'
  >;
  /** The fluid center cap (100% minus the responsive gutter). */
  contentInset: string;
}

export function TranscriptRegion({ surface, conversation, contentInset }: TranscriptRegionProps) {
  const {
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
  } = conversation;
  const {
    emptyState,
    agentPanelProps,
    renderHeader,
    renderBadge,
    renderActions,
    messageBubbleClassName,
    collapseMaxHeight,
    showMoreLabel,
    showLessLabel,
    collapseToggleClassName,
    errorClassName,
    retryButtonClassName,
    dismissButtonClassName,
    scrollToBottomClassName,
    scrollToBottomIconClassName,
    showPersistedTrace = true,
    showCopyAction = false,
    collapseUserMessages = true,
    autoScroll = true,
    retryLabel = 'Reintentar',
    dismissLabel = 'Descartar',
    persistRetryLabel = 'Reintentar guardar',
    scrollToBottomLabel = 'Ir al final',
  } = surface;

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
              agentAuthor={author}
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

          {/* The turn succeeded but the thread could not be SAVED. The framework
              surfaces it without the consumer opting in: a save that fails in
              silence lets the user trust a conversation that is not there. */}
          {persistError && (
            <TurnErrorBanner
              error={persistError}
              onRetry={retryPersist}
              onDismiss={dismissPersistError}
              className={errorClassName}
              retryLabel={persistRetryLabel}
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
