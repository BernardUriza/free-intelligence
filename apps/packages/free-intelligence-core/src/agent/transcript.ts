/**
 * Transcript bridge — fold the live agentic turn into flat chat messages.
 *
 * Pure, framework-agnostic (no React, no transport). The agent contract models
 * ONE live turn (AgentTurnState); a conversation surface needs the thread as a
 * flat list. These two helpers bridge `AgentTurnState` → `ChatMessage` so any
 * shell (fi-glass and beyond) can keep a visible transcript without re-deriving
 * the mapping. Moved here from the og118 consumer (DD-002-LESSON): a reusable
 * primitive belongs in the framework, not the app wrapper.
 */

import type { ChatMessage, MessageTrace } from '../chat/message';
import type { AgentTurnState } from './state';

/** A user message, ready to render optimistically the instant the user sends. */
export function makeUserMessage(text: string): ChatMessage {
  return { role: 'user', content: text, timestamp: new Date().toISOString() };
}

/**
 * Snapshot the turn's glass-box provenance for persistence (B3-FIGLASS-TRACE-
 * PERSISTENCE-1). Returns undefined for a plain conversational turn (no plan, no
 * tools, no sources) so those messages fold exactly as before — the trace is
 * opt-in, never bloating the simple case. The declared plan is kept even with
 * zero settled steps (the act of planning is itself the glass-box signal).
 */
function snapshotTrace(turn: AgentTurnState): MessageTrace | undefined {
  const hasPlan = turn.plan != null && turn.plan.steps.length > 0;
  const hasTools = turn.steps.length > 0;
  const hasSources = turn.sources.length > 0;
  if (!hasPlan && !hasTools && !hasSources) return undefined;
  return {
    ...(hasPlan ? { plan: turn.plan! } : {}),
    ...(hasTools ? { tools: turn.steps } : {}),
    ...(hasSources ? { sources: turn.sources } : {}),
  };
}

/**
 * Fold a finished turn's answer into an assistant message. The answer text is
 * the message content; the agentic provenance (declared plan + per-step
 * outcomes, tool calls, evidence) is snapshotted into `trace` so the durable
 * transcript re-renders the same glass-box the live turn showed — the "see the
 * execution, not just the result" differentiator survives the fold. A plain
 * conversational turn (no plan/tools/sources) folds with no `trace`, unchanged.
 * Model provenance also survives: `turn.meta.model` lands in `metadata.model`.
 */
export function foldAssistantTurn(turn: AgentTurnState): ChatMessage {
  const model = turn.meta?.model;
  const trace = snapshotTrace(turn);
  return {
    role: 'assistant',
    content: turn.text,
    timestamp: new Date().toISOString(),
    ...(model ? { metadata: { model } } : {}),
    ...(trace ? { trace } : {}),
  };
}
