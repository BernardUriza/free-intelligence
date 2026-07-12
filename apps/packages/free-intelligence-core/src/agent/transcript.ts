/**
 * Transcript bridge — fold the live agentic turn into flat chat messages.
 *
 * Pure, framework-agnostic (no React, no transport). The agent contract models
 * ONE live turn (AgentTurnState); a conversation surface needs the thread as a
 * flat list. These two helpers bridge `AgentTurnState` → `ChatMessage` so any
 * shell (fi-glass and beyond) can keep a visible transcript without re-deriving
 * the mapping. Moved here from the og118 consumer (DD-002-LESSON): a reusable
 * primitive belongs in the framework, not the app wrapper.
 *
 * NO TEXT WITHOUT AN AUTHOR: both helpers take the speaker as a REQUIRED
 * argument. A shell whose user can swap the answering persona must never fold a
 * bubble the transcript cannot attribute — the alternative (an optional author
 * the consumer may forget) is exactly how og118 spent every turn claiming
 * "og118" answered while an element actually did.
 */

import type { ChatMessage, MessageTrace } from '../chat/message';
import type { MessageAuthor } from './events';
import type { AgentTurnState } from './state';

/** A user message, ready to render optimistically the instant the user sends. */
export function makeUserMessage(text: string, author: MessageAuthor): ChatMessage {
  return { role: 'user', author, content: text, timestamp: new Date().toISOString() };
}

/**
 * Snapshot the turn's glass-box provenance for persistence (B3-FIGLASS-TRACE-
 * PERSISTENCE-1). Returns undefined for a plain conversational turn with no
 * provenance at all, so those messages fold exactly as before — the trace is
 * opt-in, never bloating the simple case. The declared plan is kept even with
 * zero settled steps (the act of planning is itself the glass-box signal), and
 * the model is kept on its own: a plain answer still knows what produced it.
 */
function snapshotTrace(turn: AgentTurnState): MessageTrace | undefined {
  const hasPlan = turn.plan != null && turn.plan.steps.length > 0;
  const hasTools = turn.steps.length > 0;
  const hasSources = turn.sources.length > 0;
  const model = turn.meta?.model?.trim() || undefined;
  if (!hasPlan && !hasTools && !hasSources && !model) return undefined;
  return {
    ...(hasPlan ? { plan: turn.plan! } : {}),
    ...(hasTools ? { tools: turn.steps } : {}),
    ...(hasSources ? { sources: turn.sources } : {}),
    ...(model ? { model } : {}),
  };
}

/**
 * Fold a finished turn's answer into an assistant message. The answer text is
 * the message content; the agentic provenance (declared plan + per-step
 * outcomes, tool calls, evidence) is snapshotted into `trace` so the durable
 * transcript re-renders the same glass-box the live turn showed — the "see the
 * execution, not just the result" differentiator survives the fold. A turn with
 * no provenance at all folds with no `trace`, unchanged.
 *
 * Model provenance rides the TRACE, not `metadata`: persistence drops metadata
 * by design (apps stash secrets there), so a model chip read from it showed on
 * the live turn and vanished on reload — a badge that was never once seen after
 * a refresh. It is provenance, and provenance persists.
 *
 * Authorship comes from the turn itself when the backend named a speaker (the
 * `author` event — the resolved persona/element); `defaultAuthor` is the agent's
 * own identity, used when it did not. Required, so the folded message always
 * knows who spoke.
 */
export function foldAssistantTurn(
  turn: AgentTurnState,
  defaultAuthor: MessageAuthor,
): ChatMessage {
  const trace = snapshotTrace(turn);
  return {
    role: 'assistant',
    author: turn.author ?? defaultAuthor,
    content: turn.text,
    timestamp: new Date().toISOString(),
    ...(trace ? { trace } : {}),
  };
}
