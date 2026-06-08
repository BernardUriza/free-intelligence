/**
 * og118 transcript helpers (DD-002A) — pure, no React, no transport.
 *
 * The agentic glass-box (AgentHook) models ONE live turn. og118's daily-driver
 * needs the conversation thread visible too, so these fold the live turn into a
 * flat ChatMessage transcript that renders above the in-flight turn. In-memory
 * only (DD-002A); persistence across refresh is DD-002B, model-side context is
 * DD-002C. The framework-level "conversation of agentic turns" is fi-glass debt
 * (residual #8 evolved) — deliberately NOT built here.
 */

import type { ChatMessage, AgentTurnState } from '@free-intelligence/core';

/** A user message, ready to render the instant the user hits send. */
export function makeUserMessage(text: string): ChatMessage {
  return { role: 'user', content: text, timestamp: new Date().toISOString() };
}

/**
 * Fold a completed turn's answer into an assistant message. The full
 * AgentTurnState snapshot rides along in metadata.turn so a future gate can
 * render the per-turn glass-box collapsed — DD-002A does NOT render it yet.
 */
export function foldAssistantTurn(state: AgentTurnState): ChatMessage {
  return {
    role: 'assistant',
    content: state.text,
    timestamp: new Date().toISOString(),
    metadata: { turn: state },
  };
}
