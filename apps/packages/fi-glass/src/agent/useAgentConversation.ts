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
 * (or reverts the optimistic message if the turn failed). No transport, no
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
 *
 * B3-FIGLASS-8 adds the TURN-FAILURE-RECOVERY contract (the staging audit found
 * a hung stream left the UI in "thinking…" forever AND persisted the optimistic
 * user message as if it were durable conversation truth):
 *  - an idle watchdog (`turnTimeoutMs`, injectable/testable) declares the turn
 *    failed when nothing changes for that long — a hung transport no longer
 *    pins the UI streaming forever;
 *  - a failed turn (timeout OR an `error` status from the transport) reverts the
 *    optimistic user message, surfaces a recoverable `turnError`, and lets the
 *    user `retry()` (re-send the same text) or `dismissError()`;
 *  - persistence is CONFIRMED-ONLY: the optimistic push is never persisted on
 *    its own, so a failed/hung turn never becomes a durable lone user message.
 *    `onMessagesChange` fires when a turn folds (user + assistant together) or
 *    when a revert returns the thread to its pre-send state.
 *
 * FIGLASS-CONTROLLED adds an OPTIONAL CONTROLLED / external-transcript mode
 * (surfaced by the Activist OS canary: a governed multi-agent WORKFLOW where one
 * `send` produces 8+ agent-handoff messages, not 1 assistant turn). The default
 * UNCONTROLLED mode folds exactly one assistant message per send, which collapses
 * an 8-message workflow into a single bubble. When the consumer passes
 * `externalMessages`, IT owns the visible thread (it maps its own transport into
 * a transcript) and this hook stops owning it:
 *  - `conversation.messages` returns `externalMessages` verbatim — no internal
 *    array, no optimistic push, no fold;
 *  - `send(text)` still drives the turn via `agent.send(text)` but does NOT push
 *    an optimistic user message and does NOT fold the finished turn (the
 *    consumer's `externalMessages` already reflects truth);
 *  - `turn` / `isStreaming` / `turnError` / `retry` / `dismissError` /
 *    `newConversation` still work — the idle watchdog and the transport-error
 *    recovery stay live so a hung/failed workflow is recoverable; the
 *    optimistic-revert in the failure paths is simply a no-op (there is nothing
 *    to revert), and the fold-on-success is skipped;
 *  - the internal-thread persistence machinery (`initialMessages`,
 *    `conversationId`, `onMessagesChange`) is bypassed — the consumer owns
 *    persistence. `initialMessages` and `externalMessages` are mutually
 *    exclusive: if both are passed, `externalMessages` wins (controlled mode).
 *  - FULLY BACKWARD COMPATIBLE: with `externalMessages` undefined, behavior is
 *    byte-identical to the uncontrolled mode above. Existing consumers (og118,
 *    insult_ai, aurity) are untouched.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import {
  type AgentHook,
  type AgentTurnState,
  type ChatMessage,
  makeUserMessage,
  foldAssistantTurn,
} from '@free-intelligence/core';

/**
 * Predicate an app passes to CLAIM a specific error class as its own. When it
 * returns true for a failed turn, the conversation still reverts the optimistic
 * message but does NOT raise the generic recoverable `turnError` — the app shows
 * its own UI instead (e.g. og118's 401 token-gate banner, where a blind "retry"
 * would just 401 again). The idle-timeout failure is never app-handled.
 */
export type AppHandledError = (turn: AgentTurnState) => boolean;

/** A recoverable failure of the in-flight turn, surfaced for retry/dismiss. */
export interface TurnError {
  /** `timeout` = the idle watchdog fired; `stream` = the transport reported error. */
  kind: 'timeout' | 'stream';
  /** Human-readable, app-displayable reason. */
  message: string;
}

/** Default idle watchdog: a turn with no state change for this long is hung. */
export const DEFAULT_TURN_TIMEOUT_MS = 60_000;

export interface UseAgentConversationOptions {
  /**
   * Controlled mode: when provided, the CONSUMER owns the visible thread. The
   * hook returns these verbatim as `conversation.messages` and stops folding —
   * `send` drives `agent.send(text)` but pushes no optimistic message and folds
   * no finished turn (the consumer maps its own transport into this transcript).
   * For workflow adapters whose single send yields many agent-handoff messages
   * (the 1-send -> 8+ messages case the single-turn fold cannot express; the
   * Activist OS canary that surfaced this). Mutually exclusive with
   * `initialMessages`/`conversationId`/`onMessagesChange` (those are bypassed —
   * the consumer owns persistence); if both `externalMessages` and
   * `initialMessages` are passed, `externalMessages` wins. Undefined =
   * uncontrolled (the hook owns the thread, byte-identical to before).
   */
  externalMessages?: ChatMessage[];
  /** Identity of the active conversation. When it changes, the thread re-hydrates. (Ignored in controlled mode.) */
  conversationId?: string | null;
  /** Messages to seed the thread with (the active conversation's stored transcript). (Ignored in controlled mode.) */
  initialMessages?: ChatMessage[];
  /** Called when the thread changes from real activity (fold/revert) — a persist hook. (Not called in controlled mode.) */
  onMessagesChange?: (messages: ChatMessage[]) => void;
  /**
   * Idle watchdog in ms: if the live turn's state does not change for this long
   * while streaming, the turn is declared failed (timeout). Measured since the
   * LAST turn-state change, not since send — a long-but-active turn (streaming
   * tokens, running steps) keeps resetting it and never trips. Pass a small
   * value in tests; `0` disables the watchdog. Defaults to 60s.
   */
  turnTimeoutMs?: number;
  /**
   * Claim a specific error class as app-handled (see {@link AppHandledError}).
   * Such a failure still reverts the optimistic message but is NOT surfaced as a
   * generic `turnError` — the app renders its own UI for it. Timeouts ignore this.
   */
  isAppHandledError?: AppHandledError;
}

export interface AgentConversation {
  /** The visible thread of completed turns (user + assistant), in send order. */
  messages: ChatMessage[];
  /** The current/live turn's reduced state (for the in-flight glass-box). */
  turn: AgentTurnState;
  /**
   * Whether a turn is actively streaming. This is the CONVERSATION's view, not
   * the transport's: once the watchdog declares a turn hung, this is false even
   * if the underlying `agent.isStreaming` is still stuck true — so the surface
   * leaves the "thinking…" state and can render the recoverable error instead.
   */
  isStreaming: boolean;
  /** A recoverable failure of the last turn (timeout/stream), or null. */
  turnError: TurnError | null;
  /** Send a message: pushes it optimistically, then drives the agent turn. */
  send: (text: string) => void;
  /** Re-send the last user text after a failure. No-op if there is nothing to retry. */
  retry: () => void;
  /** Clear the current turnError without re-sending (the optimistic msg is already reverted). */
  dismissError: () => void;
  /** Clear the whole thread and reset the underlying turn/session. */
  newConversation: () => void;
}

export function useAgentConversation(
  agent: AgentHook,
  options: UseAgentConversationOptions = {},
): AgentConversation {
  const {
    externalMessages,
    conversationId,
    initialMessages,
    onMessagesChange,
    turnTimeoutMs = DEFAULT_TURN_TIMEOUT_MS,
    isAppHandledError,
  } = options;

  // Controlled mode: the consumer owns the visible thread via externalMessages.
  // The hook then drives the turn (and its recovery) but never owns/folds/persists
  // the transcript. `externalMessages` wins over `initialMessages` if both passed.
  const controlled = externalMessages !== undefined;

  const [messages, setMessages] = useState<ChatMessage[]>(
    initialMessages ?? [],
  );
  // Read the latest controlled flag inside effects without re-arming them on it.
  const controlledRef = useRef(controlled);
  controlledRef.current = controlled;
  const [turnError, setTurnError] = useState<TurnError | null>(null);
  // The conversation's own "the watchdog killed this turn" flag. Lets us drop
  // out of streaming even when the transport's isStreaming is stuck true.
  const [timedOut, setTimedOut] = useState(false);

  // True while a turn we optimistically pushed is still in flight; gates the fold.
  const pending = useRef(false);
  // Latest visible thread, read inside the stable `send` closure WITHOUT adding
  // `messages` to its deps (which would rebuild send every keystroke-fold). Used
  // to hand the transport the confirmed history for storeless-backend continuity.
  const messagesRef = useRef(messages);
  messagesRef.current = externalMessages ?? messages;
  // Latest agent, read inside timers/effects WITHOUT depending on its identity —
  // transport hooks often return a fresh object each render, which would re-arm
  // the idle watchdog every render instead of on real turn progress.
  const agentRef = useRef(agent);
  agentRef.current = agent;
  // Latest app-handled-error predicate, read without depending on its identity
  // (apps often pass a fresh arrow each render).
  const appHandledRef = useRef(isAppHandledError);
  appHandledRef.current = isAppHandledError;
  // Last text the user sent — replayed by retry().
  const lastSent = useRef<string | null>(null);
  // Latest seed, read without retriggering the hydration effect on array identity.
  const initialRef = useRef(initialMessages);
  initialRef.current = initialMessages;
  // Suppress onMessagesChange for changes that are NOT a confirmed/settled turn:
  // the mount seed, a conversation switch, and the optimistic push. Persistence
  // is confirmed-only, so a failed/hung turn never leaves a durable lone message.
  const skipPersist = useRef(true);
  // Skip the conversationId effect on mount (useState already seeded the thread).
  const mounted = useRef(false);

  // Revert the optimistic user message that is still the thread's tail. Used by
  // both failure paths (timeout watchdog + transport error). Returns the thread
  // to its pre-send state so persistence never records an unanswered turn.
  const revertOptimistic = useCallback(() => {
    // Controlled mode never pushed an optimistic message — nothing to revert.
    if (controlledRef.current) return;
    setMessages((prev) => {
      const last = prev[prev.length - 1];
      return last?.role === 'user' ? prev.slice(0, -1) : prev;
    });
  }, []);

  const send = useCallback(
    (text: string) => {
      const t = text.trim();
      if (!t || agent.isStreaming) return;
      lastSent.current = t;
      setTurnError(null);
      setTimedOut(false);
      if (!controlled) {
        // Uncontrolled: push the user message optimistically (and gate persist).
        // Controlled: the consumer's externalMessages already reflects the send.
        skipPersist.current = true; // the optimistic push is not a confirmed turn
        setMessages((prev) => [...prev, makeUserMessage(t)]);
      }
      pending.current = true;
      // Hand the transport the confirmed thread (prior turns, NOT this message) so
      // a storeless backend can replay it for continuity. The transport that needs
      // it forwards it; one that doesn't ignores `meta`. messagesRef is the thread
      // BEFORE the optimistic push above (same render's state), so the current
      // message is never duplicated into history.
      void agent.send(t, { history: messagesRef.current });
    },
    [agent, controlled],
  );

  const retry = useCallback(() => {
    if (lastSent.current) send(lastSent.current);
  }, [send]);

  const dismissError = useCallback(() => {
    setTurnError(null);
    setTimedOut(false);
  }, []);

  // Fold the finished turn once it stops streaming. Effect-based on purpose: the
  // transport hook owns the turn lifecycle, the conversation only observes it.
  useEffect(() => {
    if (agent.isStreaming || !pending.current) return;
    pending.current = false;
    if (agent.turn.status === 'error') {
      // Transport reported a failure: always revert the optimistic user message
      // (never drop it silently). Surface a generic recoverable error UNLESS the
      // app claims this error class (e.g. og118's 401 token gate, which shows its
      // own banner — a blind retry there would just 401 again).
      revertOptimistic();
      if (!appHandledRef.current?.(agent.turn)) {
        setTurnError({
          kind: 'stream',
          message: agent.turn.errorMessage || 'La respuesta falló. Intenta de nuevo.',
        });
      }
      return;
    }
    // Controlled mode never folds: the consumer's externalMessages already holds
    // the (possibly multi-message) turn it mapped from its own transport.
    if (controlledRef.current) return;
    if (agent.turn.text) {
      // Clean finish with an answer: fold it in. This is the confirmed turn —
      // let persistence record user + assistant together (skipPersist stays
      // false through this settled emit).
      skipPersist.current = false;
      setMessages((prev) => [...prev, foldAssistantTurn(agent.turn)]);
    }
  }, [agent.isStreaming, agent.turn, revertOptimistic]);

  // Idle watchdog: while a pushed turn is streaming, arm a timer that re-arms on
  // every turn-state change (so an active turn never trips). If it fires, the
  // transport is hung — declare the turn failed, abort it, revert the optimistic
  // message, and surface a recoverable timeout error.
  useEffect(() => {
    if (turnTimeoutMs <= 0) return;
    if (!agent.isStreaming || !pending.current || timedOut) return;
    const timer = setTimeout(() => {
      pending.current = false;
      agentRef.current.abort?.();
      revertOptimistic();
      setTimedOut(true);
      setTurnError({
        kind: 'timeout',
        message: 'La respuesta tardó demasiado. Intenta de nuevo.',
      });
    }, turnTimeoutMs);
    return () => clearTimeout(timer);
    // Re-arm on real turn progress (agent.turn is immutable, changes only on
    // events) — NOT on agent identity, so a fresh agent object per render does
    // not reset the watchdog. That makes this a true idle watchdog.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [agent.isStreaming, agent.turn, timedOut, turnTimeoutMs, revertOptimistic]);

  // Re-hydrate when the active conversation changes: load the new seed, drop any
  // pending fold/error, and reset the live turn so the start screen shows correctly.
  useEffect(() => {
    if (!mounted.current) {
      mounted.current = true;
      return;
    }
    // Controlled mode: the consumer owns the thread + persistence, so a
    // conversationId change never re-hydrates an internal array.
    if (controlledRef.current) return;
    skipPersist.current = true;
    pending.current = false;
    setTurnError(null);
    setTimedOut(false);
    setMessages(initialRef.current ?? []);
    agent.reset?.();
    // Re-hydrate strictly on identity change, not on every seed-array change.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [conversationId]);

  // Notify on confirmed message changes; skip the seed/hydration/optimistic emits.
  // Controlled mode never persists via this hook — the consumer owns persistence.
  useEffect(() => {
    if (controlledRef.current) return;
    if (skipPersist.current) {
      skipPersist.current = false;
      return;
    }
    onMessagesChange?.(messages);
    // onMessagesChange is read via latest closure; depend only on messages.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [messages]);

  const newConversation = useCallback(() => {
    skipPersist.current = true;
    setTurnError(null);
    setTimedOut(false);
    // Controlled mode: the consumer owns the thread, so clearing the internal
    // array is a no-op for what's shown; still reset the live turn/session.
    if (!controlled) setMessages([]);
    pending.current = false;
    agent.reset?.();
  }, [agent, controlled]);

  return {
    messages: externalMessages ?? messages,
    turn: agent.turn,
    isStreaming: agent.isStreaming && !timedOut,
    turnError,
    send,
    retry,
    dismissError,
    newConversation,
  };
}
