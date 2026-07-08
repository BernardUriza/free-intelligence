/**
 * fi-glass · conversation-surface/persistedTraceTurn — rebuild a finished
 * AgentTurnState from a persisted message trace so the live AgentPanel can
 * re-render the glass-box of an already-folded turn
 * (B3-FIGLASS-TRACE-PERSISTENCE-1). Status is 'done' (the turn settled);
 * returns null when the message carries no renderable trace, so a plain
 * message renders unchanged. No new renderer — the persisted history reuses
 * the live components.
 */

import type { AgentTurnState, ChatMessage } from '@free-intelligence/core';

export function persistedTraceTurn(message: ChatMessage): AgentTurnState | null {
  const trace = message.trace;
  if (!trace) return null;
  const hasContent =
    (trace.plan?.steps.length ?? 0) > 0 ||
    (trace.tools?.length ?? 0) > 0 ||
    (trace.sources?.length ?? 0) > 0;
  if (!hasContent) return null;
  return {
    plan: trace.plan ?? null,
    steps: trace.tools ?? [],
    text: message.content,
    sources: trace.sources ?? [],
    meta: null,
    status: 'done',
  };
}
