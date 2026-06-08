'use client';

/**
 * useAgentConversation — turn an AgentHook (one live glass-box turn) into a
 * visible conversation thread. The reusable answer to DD-002: the consumer
 * (og118) was keeping its own transcript; that primitive belongs here so every
 * fi-glass shell inherits it.
 *
 * The transport hook (the app's AgentHook) owns ONE live turn. This layer only
 * observes that turn's lifecycle: it pushes the user message optimistically on
 * send, and when the turn stops streaming it folds the answer into the thread
 * (or reverts the optimistic message if the turn errored). No transport, no
 * endpoint, no token, no branding here — those stay in the app.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import {
  type AgentHook,
  type AgentTurnState,
  type ChatMessage,
  makeUserMessage,
  foldAssistantTurn,
} from '@free-intelligence/core';

export interface AgentConversation {
  /** The visible thread of completed turns (user + assistant), in send order. */
  messages: ChatMessage[];
  /** The current/live turn's reduced state (for the in-flight glass-box). */
  turn: AgentTurnState;
  /** Whether a turn is actively streaming. */
  isStreaming: boolean;
  /** Send a message: pushes it optimistically, then drives the agent turn. */
  send: (text: string) => void;
  /** Clear the whole thread and reset the underlying turn/session. */
  newConversation: () => void;
}

export function useAgentConversation(agent: AgentHook): AgentConversation {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  // True while a turn we optimistically pushed is still in flight; gates the fold.
  const pending = useRef(false);

  const send = useCallback(
    (text: string) => {
      const t = text.trim();
      if (!t || agent.isStreaming) return;
      setMessages((prev) => [...prev, makeUserMessage(t)]);
      pending.current = true;
      void agent.send(t);
    },
    [agent],
  );

  // Fold the finished turn once it stops streaming. Effect-based on purpose: the
  // transport hook owns the turn lifecycle, the conversation only observes it.
  useEffect(() => {
    if (agent.isStreaming || !pending.current) return;
    pending.current = false;
    setMessages((prev) => {
      // Early failure (e.g. 401): revert the optimistic user message.
      if (agent.turn.status === 'error') return prev.slice(0, -1);
      // Clean finish with an answer: append it to the thread.
      if (agent.turn.text) return [...prev, foldAssistantTurn(agent.turn)];
      return prev;
    });
  }, [agent.isStreaming, agent.turn]);

  const newConversation = useCallback(() => {
    setMessages([]);
    pending.current = false;
    agent.reset?.();
  }, [agent]);

  return {
    messages,
    turn: agent.turn,
    isStreaming: agent.isStreaming,
    send,
    newConversation,
  };
}
