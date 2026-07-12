'use client';

/**
 * fi-glass · conversation-surface/TranscriptMessages — the conversation body:
 * completed turns (user + assistant) each in a bubble, then the live streaming
 * turn (glass-box panel + streaming bubble).
 *
 * B3-FIGLASS-TRACE-PERSISTENCE-1 — an assistant message that carries a
 * persisted glass-box trace re-renders the SAME AgentPanel above its answer,
 * exactly as the live turn did, so reloading a conversation shows the
 * execution and not just the result.
 */

import { Fragment, type ReactNode } from 'react';
import type { AgentTurnState, ChatMessage, MessageAuthor } from '@free-intelligence/core';
import { MessageContent, MessageBubble, CopyButton } from '../../../../messages';
import {
  MessageAuthorHeader,
  defaultMessageHeader,
} from '../../../../messages/MessageAuthorHeader';
import { defaultMessageBadge } from '../../../../messages/MessageModelBadge';
import { DEFAULT_USER_AUTHOR } from '../../../useAgentConversation';
import { AgentPanel, type AgentPanelProps } from '../../../AgentPanel';
import { persistedTraceTurn } from '../../persistedTraceTurn';

export interface TranscriptMessagesProps {
  messages: ChatMessage[];
  turn: AgentTurnState;
  isStreaming: boolean;
  /** The agent's own identity — attributes the live turn until it names itself. */
  agentAuthor: MessageAuthor;
  /** The human's identity. Defaults to the framework's. */
  userAuthor?: MessageAuthor;
  showPersistedTrace: boolean;
  agentPanelProps?: Partial<Omit<AgentPanelProps, 'turn'>>;
  showCopyAction: boolean;
  renderHeader?: (message: ChatMessage) => ReactNode;
  renderBadge?: (message: ChatMessage) => ReactNode;
  renderActions?: (message: ChatMessage) => ReactNode;
  resolveBubbleClass: (message: ChatMessage) => string | undefined;
  collapseUserMessages: boolean;
  collapseMaxHeight?: number;
  showMoreLabel?: string;
  showLessLabel?: string;
  collapseToggleClassName?: string;
}

export function TranscriptMessages({
  messages,
  turn,
  isStreaming,
  agentAuthor,
  userAuthor,
  showPersistedTrace,
  agentPanelProps,
  showCopyAction,
  renderHeader,
  renderBadge,
  renderActions,
  resolveBubbleClass,
  collapseUserMessages,
  collapseMaxHeight,
  showMoreLabel,
  showLessLabel,
  collapseToggleClassName,
}: TranscriptMessagesProps) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      {messages.map((m, i) => {
        const traceTurn =
          showPersistedTrace && m.role === 'assistant' ? persistedTraceTurn(m) : null;
        // Index-only keys leak per-instance state (the user-message collapse
        // toggle) across conversations: switching threads reuses indices 0..n
        // and React reuses the instances. The timestamp disambiguates threads;
        // the index disambiguates same-instant messages within one.
        return (
          <Fragment key={`${m.timestamp}-${i}`}>
            {traceTurn && <AgentPanel turn={traceTurn} {...agentPanelProps} />}
            <MessageBubble
              role={m.role}
              // The framework attributes the bubble off `message.author`;
              // `renderHeader` is the consumer's escape hatch, not the only path
              // to a header (og118's hardcoded "og118" row was exactly that bug).
              header={
                renderHeader
                  ? renderHeader(m)
                  : defaultMessageHeader(m, agentAuthor, userAuthor ?? DEFAULT_USER_AUTHOR)
              }
              // Model provenance, off the persisted trace — the framework shows
              // it without the consumer wiring a badge (og118's own chip read a
              // field nothing ever wrote, so it never rendered once).
              badge={renderBadge ? renderBadge(m) : defaultMessageBadge(m)}
              actions={
                renderActions?.(m) ??
                (showCopyAction ? <CopyButton content={m.content} /> : undefined)
              }
              className={resolveBubbleClass(m)}
            >
              <MessageContent
                isUser={m.role === 'user'}
                content={m.content}
                // B3-FIGLASS-12: only USER messages clamp (ChatGPT parity) —
                // a long pasted prompt folds behind "Mostrar más"; assistant
                // answers always render whole.
                collapsible={collapseUserMessages && m.role === 'user'}
                collapsedMaxHeight={collapseMaxHeight}
                showMoreLabel={showMoreLabel}
                showLessLabel={showLessLabel}
                collapseToggleClassName={collapseToggleClassName}
              />
            </MessageBubble>
          </Fragment>
        );
      })}

      {/* Live turn: the glass-box STICKS to the top of the scroll viewport while
          the answer streams beneath it. Without this the panel scrolled away as
          soon as the answer outgrew the viewport — measured at y = -2921px on a
          real og118 turn — so the surface's promise ("watch it plan") broke on
          exactly the long, multi-step answers a plan exists for.

          A sticky element only travels within ITS OWN parent, so the panel and
          the streaming answer share one wrapper: the answer's height IS the
          panel's sticky runway. Sticking it as a lone child of the transcript
          column gave it a runway of ~0 and it scrolled off anyway.

          It sticks against the transcript's `overflow-y: auto` ancestor; a
          consumer without one degrades to the previous static layout. The panel
          needs an opaque surface to sit over the text (og118 supplies one via
          `agentPanelProps.classNames.card`); `data-fi-live-trace` is the hook
          for a consumer that wants to dress the rail itself. */}
      {isStreaming && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <div data-fi-live-trace="" style={{ position: 'sticky', top: 0, zIndex: 1 }}>
            <AgentPanel turn={turn} {...agentPanelProps} />
          </div>
          {turn.text && (
            <MessageBubble
              role="assistant"
              // Attributed from its FIRST character: the backend announces the
              // speaker (`author` event) before any token, so the streaming
              // bubble already says "Yodo" — it is never re-labelled on fold.
              header={<MessageAuthorHeader author={turn.author ?? agentAuthor} />}
              className={resolveBubbleClass({
                role: 'assistant',
                content: turn.text,
                timestamp: '',
              })}
            >
              <MessageContent isUser={false} content={turn.text} isStreaming />
            </MessageBubble>
          )}
        </div>
      )}
    </div>
  );
}
