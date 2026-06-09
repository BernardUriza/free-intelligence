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
 *
 * DD-002B1.2 adds OPTIONAL persistence hooks (all backward-compatible — calling
 * `useAgentConversation(agent)` with no options behaves exactly as before):
 *  - `initialMessages` seeds the thread (rehydrate a stored conversation);
 *  - `conversationId` identifies the active conversation — when it CHANGES the
 *    thread re-hydrates to `initialMessages` and the live turn resets;
 *  - `onMessagesChange` fires on real activity (send / fold) so a manager can
 *    persist — it is intentionally NOT called during the initial seed or a
 *    switch, so loading a conversation never clobbers it with an empty echo.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import {
  type AgentHook,
  type AgentTurnState,
  type ChatMessage,
  makeUserMessage,
  foldAssistantTurn,
} from '@free-intelligence/core';

export interface UseAgentConversationOptions {
  /** Identity of the active conversation. When it changes, the thread re-hydrates. */
  conversationId?: string | null;
  /** Messages to seed the thread with (the active conversation's stored transcript). */
  initialMessages?: ChatMessage[];
  /** Called when the thread changes from real activity (send/fold) — a persist hook. */
  onMessagesChange?: (messages: ChatMessage[]) => void;
}

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

export function useAgentConversation(
  agent: AgentHook,
  options: UseAgentConversationOptions = {},
): AgentConversation {
  const { conversationId, initialMessages, onMessagesChange } = options;

  const [messages, setMessages] = useState<ChatMessage[]>(
    initialMessages ?? [],
  );
  // True while a turn we optimistically pushed is still in flight; gates the fold.
  const pending = useRef(false);
  // Latest seed, read without retriggering the hydration effect on array identity.
  const initialRef = useRef(initialMessages);
  initialRef.current = initialMessages;
  // Suppress onMessagesChange for changes that come from seeding/hydration (not
  // real activity), so loading a conversation never echoes an empty/duplicate
  // persist. Starts true to skip the mount seed.
  const hydrating = useRef(true);
  // Skip the conversationId effect on mount (useState already seeded the thread).
  const mounted = useRef(false);

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

  // Re-hydrate when the active conversation changes: load the new seed, drop any
  // pending fold, and reset the live turn so the start screen shows correctly.
  useEffect(() => {
    if (!mounted.current) {
      mounted.current = true;
      return;
    }
    hydrating.current = true;
    pending.current = false;
    setMessages(initialRef.current ?? []);
    agent.reset?.();
    // Re-hydrate strictly on identity change, not on every seed-array change.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [conversationId]);

  // Notify on real message changes; skip the seed/hydration emits.
  useEffect(() => {
    if (hydrating.current) {
      hydrating.current = false;
      return;
    }
    onMessagesChange?.(messages);
    // onMessagesChange is read via latest closure; depend only on messages.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [messages]);

  const newConversation = useCallback(() => {
    hydrating.current = true;
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
