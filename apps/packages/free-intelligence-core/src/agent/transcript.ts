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

import type { ChatMessage } from '../chat/message';
import type { AgentTurnState } from './state';

/** A user message, ready to render optimistically the instant the user sends. */
export function makeUserMessage(text: string): ChatMessage {
  return { role: 'user', content: text, timestamp: new Date().toISOString() };
}

/**
 * Fold a finished turn's answer into an assistant message. Keeps only the
 * material-agnostic content (no AgentTurnState snapshot) — a future gate can add
 * per-turn glass-box rendering without bloating the ChatMessage contract now.
 */
export function foldAssistantTurn(turn: AgentTurnState): ChatMessage {
  return { role: 'assistant', content: turn.text, timestamp: new Date().toISOString() };
}
