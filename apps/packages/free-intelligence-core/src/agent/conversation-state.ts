/**
 * ConversationState — the reduced state of a whole agentic CONVERSATION (the
 * thread across turns), plus the pure `applyConversationEvent` reducer that
 * derives it.
 *
 * Sibling of {@link ./state} one level up: `AgentTurnState` reduces the wire
 * events of ONE streaming turn; this reduces the lifecycle of the conversation
 * those turns live in — the optimistic push, the fold, the revert that hands the
 * user's words back, the recoverable-failure banners, persistence bookkeeping.
 *
 * WHY IT MOVED HERE (framework-first-canary, the demotion's mirror): fi-glass's
 * `useAgentConversation` held this logic across 7 `useState` + 10 `useRef` in a
 * 575-line hook, so the rules of the machine — "a failed turn must never cost
 * the user their words", "an optimistic push is not a confirmed turn" — could
 * only be exercised by mounting React and driving a fake transport. They are not
 * React rules; they are conversation rules, identical for every shell. Here they
 * are one value and one function, testable with plain assertions.
 *
 * Pure: no React, no transport, no timers, no I/O. Immutable: every event
 * returns a new state object. Time enters as an EVENT (`turn_timeout`), never as
 * a clock read — same discipline as the turn reducer's heartbeat counter.
 */

import type { ChatMessage, MessageImage } from '../chat/message';
import type { MessageAuthor } from './events';
import type { AgentTurnState } from './state';
import { makeUserMessage, foldAssistantTurn } from './transcript';

/** Why a turn failed, in terms a shell can render a recovery banner from. */
export interface TurnFailure {
  kind: 'stream' | 'timeout';
  message: string;
}

/**
 * What a failed turn hands back so the shell can restore it into the composer.
 * Carries the WHOLE message: returning only the text let a shell re-send a
 * prompt whose images had silently ceased to exist.
 */
export interface UnsentDraft {
  text: string | null;
  images: MessageImage[] | null;
}

/** The reduced state of the conversation. */
export interface ConversationState {
  /** The visible thread. */
  messages: ChatMessage[];
  /** Set while an optimistically-pushed turn is still in flight; gates the fold. */
  pending: boolean;
  /** A recoverable turn failure the shell renders instead of a zombie panel. */
  failure: TurnFailure | null;
  /** True once a turn timed out; keeps the watchdog from re-arming on it. */
  timedOut: boolean;
  /** What a failed turn handed back, for the shell to restore. */
  unsent: UnsentDraft;
  /** The last send, replayed verbatim by a retry (text AND images). */
  lastSent: { text: string; images?: MessageImage[] } | null;
  /**
   * True when the current `messages` change is NOT a confirmed, settled turn
   * (the mount seed, a conversation switch, the optimistic push). A shell
   * persists only when this is false, so a failed turn never leaves a durable
   * lone user message.
   */
  skipPersist: boolean;
}

export type ConversationEvent =
  /** The user sent. `controlled` shells do not get an optimistic push. */
  | {
      type: 'send';
      text: string;
      images?: MessageImage[];
      author: MessageAuthor;
      controlled: boolean;
    }
  /** The transport finished cleanly. Folds the assistant turn in. */
  | { type: 'turn_settled'; turn: AgentTurnState; author: MessageAuthor; controlled: boolean }
  /**
   * The transport reported failure. `appHandled` means the app renders its own
   * banner for this error class (e.g. a 401 token gate), so the generic
   * recoverable failure is suppressed — the revert still happens either way.
   */
  | { type: 'turn_failed'; message?: string; controlled: boolean; appHandled?: boolean }
  /** The idle watchdog fired. Time as an event keeps the reducer pure. */
  | { type: 'turn_timeout'; controlled: boolean }
  | { type: 'dismiss_failure' }
  /** The shell restored `unsent` into its composer. */
  | { type: 'clear_unsent' }
  /** Load a different conversation (or start a fresh one). */
  | { type: 'hydrate'; messages: ChatMessage[] }
  /**
   * The shell CONSUMED the skip: it saw `skipPersist` and declined to persist
   * this change. One-shot — the flag clears so the NEXT confirmed change
   * persists normally. (Getting this backwards makes the shell skip forever and
   * nothing is ever saved.)
   */
  | { type: 'persist_skip_consumed' };

export function initialConversationState(seed: ChatMessage[] = []): ConversationState {
  return {
    messages: seed,
    pending: false,
    failure: null,
    timedOut: false,
    unsent: { text: null, images: null },
    lastSent: null,
    // The mount seed is not a confirmed turn.
    skipPersist: true,
  };
}

const NO_DRAFT: UnsentDraft = { text: null, images: null };

/**
 * Revert the optimistic user message that is still the thread's tail, handing
 * its content back as `unsent`.
 *
 * Reverting used to DESTROY what the user wrote: the message left the thread and
 * existed nowhere else, so a turn the watchdog killed took the prompt with it.
 * Both failure paths (transport error, timeout) route through here so neither can
 * forget — and it hands back the images too, because the composer already cleared
 * its drafts on send.
 */
function revertOptimistic(state: ConversationState, controlled: boolean): ConversationState {
  // A controlled shell never pushed an optimistic message — nothing to revert.
  if (controlled) return state;
  const last = state.messages[state.messages.length - 1];
  if (last?.role !== 'user') return state;
  return {
    ...state,
    messages: state.messages.slice(0, -1),
    unsent: {
      text: last.content,
      images: last.images && last.images.length > 0 ? last.images : null,
    },
  };
}

/** Pure reducer: apply one conversation event, returning a new state. */
export function applyConversationEvent(
  state: ConversationState,
  event: ConversationEvent,
): ConversationState {
  switch (event.type) {
    case 'send': {
      const text = event.text.trim();
      const images = event.images && event.images.length > 0 ? event.images : undefined;
      // An image-only send is valid (the picture IS the message); a truly empty
      // one is a no-op.
      if (!text && !images) return state;
      const next: ConversationState = {
        ...state,
        pending: true,
        failure: null,
        timedOut: false,
        // A new send supersedes any draft still waiting to be recovered.
        unsent: NO_DRAFT,
        lastSent: { text, ...(images ? { images } : {}) },
        // The optimistic push is not a confirmed turn.
        skipPersist: true,
      };
      if (event.controlled) return next;
      return {
        ...next,
        messages: [...state.messages, makeUserMessage(text, event.author, images)],
      };
    }

    case 'turn_settled': {
      if (!state.pending) return state;
      const base = { ...state, pending: false };
      // Controlled shells never fold: the consumer's own thread already holds the
      // turn it mapped from its transport.
      if (event.controlled || !event.turn.text) return base;
      return {
        ...base,
        messages: [...state.messages, foldAssistantTurn(event.turn, event.author)],
        // A settled turn IS confirmed — this one gets persisted.
        skipPersist: false,
      };
    }

    case 'turn_failed': {
      if (!state.pending) return state;
      const reverted = revertOptimistic({ ...state, pending: false }, event.controlled);
      // The revert always happens; only the generic banner is suppressed when the
      // app owns this error class.
      if (event.appHandled) return reverted;
      return {
        ...reverted,
        failure: {
          kind: 'stream',
          message: event.message || 'La respuesta falló. Intenta de nuevo.',
        },
      };
    }

    case 'turn_timeout': {
      if (!state.pending || state.timedOut) return state;
      return {
        ...revertOptimistic({ ...state, pending: false }, event.controlled),
        timedOut: true,
        failure: { kind: 'timeout', message: 'La respuesta tardó demasiado. Intenta de nuevo.' },
      };
    }

    case 'dismiss_failure':
      return state.failure === null ? state : { ...state, failure: null, timedOut: false };

    case 'clear_unsent':
      return state.unsent.text === null && state.unsent.images === null
        ? state
        : { ...state, unsent: NO_DRAFT };

    case 'hydrate':
      return { ...initialConversationState(event.messages), lastSent: state.lastSent };

    case 'persist_skip_consumed':
      return state.skipPersist ? { ...state, skipPersist: false } : state;

    default:
      return state;
  }
}
