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
import type { AgentTurnState, ChatMessage } from '@free-intelligence/core';
import { MessageContent, MessageBubble, CopyButton } from '../../../messages';
import { AgentPanel, type AgentPanelProps } from '../../AgentPanel';
import { persistedTraceTurn } from '../persistedTraceTurn';

export interface TranscriptMessagesProps {
  messages: ChatMessage[];
  turn: AgentTurnState;
  isStreaming: boolean;
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
        return (
          <Fragment key={i}>
            {traceTurn && <AgentPanel turn={traceTurn} {...agentPanelProps} />}
            <MessageBubble
              role={m.role}
              header={renderHeader?.(m)}
              badge={renderBadge?.(m)}
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

      {/* Live turn: glass-box trace stays as-is, streaming answer in a bubble */}
      {isStreaming && <AgentPanel turn={turn} {...agentPanelProps} />}
      {isStreaming && turn.text && (
        <MessageBubble
          role="assistant"
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
  );
}
