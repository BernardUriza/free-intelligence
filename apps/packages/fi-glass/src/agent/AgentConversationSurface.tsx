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
 */

import { useState, type ReactNode } from 'react';
import { Composer } from '../composer';
import { MessageContent } from '../messages';
import { AgentPanel, type AgentPanelProps } from './AgentPanel';
import type { AgentConversation } from './useAgentConversation';

export interface AgentConversationSurfaceProps {
  /** The conversation state + actions from `useAgentConversation`. */
  conversation: AgentConversation;
  /** Composer placeholder copy (app-owned). */
  composerPlaceholder?: string;
  /** Label for the new-conversation button. Default: "New chat". */
  newChatLabel?: string;
  /** Rendered when the thread is empty and idle (e.g. an app start screen). */
  emptyState?: ReactNode;
  /** Slot rendered just above the composer (e.g. an app's auth banner). */
  aboveComposer?: ReactNode;
  /** Pass-through styling/icons for the live-turn AgentPanel. */
  agentPanelProps?: Partial<Omit<AgentPanelProps, 'turn'>>;
  /** Composer wrapper class (style hook for the app). */
  composerAreaClassName?: string;
  /** Composer textarea class (style hook for the app). */
  composerTextareaClassName?: string;
}

export function AgentConversationSurface({
  conversation,
  composerPlaceholder,
  newChatLabel = 'New chat',
  emptyState,
  aboveComposer,
  agentPanelProps,
  composerAreaClassName,
  composerTextareaClassName,
}: AgentConversationSurfaceProps) {
  const { messages, turn, isStreaming, send, newConversation } = conversation;
  const [input, setInput] = useState('');

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

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100dvh', maxWidth: 760, margin: '0 auto' }}>
      <div style={{ flex: 1, overflowY: 'auto', padding: '1.25rem 1rem' }}>
        {idle ? (
          emptyState
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {/* Transcript: completed turns (user + assistant) */}
            {messages.map((m, i) => (
              <MessageContent key={i} isUser={m.role === 'user'} content={m.content} />
            ))}

            {/* Live turn: glass-box trace + streaming answer (current turn only) */}
            {isStreaming && <AgentPanel turn={turn} {...agentPanelProps} />}
            {isStreaming && turn.text && (
              <div style={{ paddingTop: '0.5rem' }}>
                <MessageContent isUser={false} content={turn.text} isStreaming />
              </div>
            )}
          </div>
        )}
      </div>

      <div style={{ padding: '0.75rem 1rem 1.25rem', borderTop: '1px solid rgba(255,255,255,0.06)' }}>
        {hasThread && (
          <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '0.5rem' }}>
            <button
              onClick={newConversation}
              disabled={isStreaming}
              style={{
                padding: '0.35rem 0.75rem',
                borderRadius: 8,
                border: '1px solid rgba(255,255,255,0.15)',
                background: 'transparent',
                color: '#94a3b8',
                fontSize: '0.8rem',
                cursor: isStreaming ? 'not-allowed' : 'pointer',
                opacity: isStreaming ? 0.5 : 1,
              }}
            >
              {newChatLabel}
            </button>
          </div>
        )}
        {aboveComposer}
        <Composer
          message={input}
          loading={isStreaming}
          placeholder={composerPlaceholder}
          onMessageChange={setInput}
          onSend={onSend}
          areaClassName={composerAreaClassName}
          textareaClassName={composerTextareaClassName}
        />
      </div>
    </div>
  );
}
