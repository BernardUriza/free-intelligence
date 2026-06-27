import type { AgentPlan } from '../agent/state';
import type { ToolCall } from '../agent/events';

/**
 * MessageTrace — the persisted glass-box snapshot of a finished agentic turn.
 *
 * The differentiator is "see the execution, not just the result": during the
 * stream you watch the plan declared and the steps walked, but a folded message
 * historically kept only the answer text (see {@link foldAssistantTurn}). This
 * carries the agentic provenance — the declared plan with its per-step outcomes,
 * the tool calls, the evidence — INTO the durable transcript, so reloading a
 * conversation re-renders the same glass-box the live turn showed.
 *
 * Reuses the live agent contract types verbatim ({@link AgentPlan},
 * {@link ToolCall}); persistence is just a snapshot of the reduced turn state,
 * not a parallel shape. Every field is optional: a plain conversational turn
 * (no plan, no tools) folds to a message with no `trace`, unchanged.
 */
export interface MessageTrace {
  /** The declared plan with per-step status/summary/outcome, if the turn planned. */
  plan?: AgentPlan;
  /** The tool calls made during the turn, if any. */
  tools?: ToolCall[];
  /** Evidence references surfaced during the turn, if any. */
  sources?: string[];
}

/**
 * ChatMessage — the material-agnostic shape of one chat message.
 *
 * Apps may use a richer message type (e.g. aurity's FIMessage with typed
 * metadata); ChatHook is generic over the message type and defaults to this.
 * Pure data — no React, no styling.
 */
export interface ChatMessage {
  /** Stable id (optional for transient/streaming messages). */
  id?: string;
  /** Who authored the message. */
  role: 'user' | 'assistant';
  /** The message text. */
  content: string;
  /** Optional model reasoning rendered before the content. */
  thinking?: string | null;
  /** ISO 8601 timestamp. */
  timestamp: string;
  /** App-specific metadata (tone, voice, model, …). */
  metadata?: Record<string, unknown>;
  /**
   * Persisted glass-box snapshot of the agentic turn that produced this message
   * (assistant messages only). Absent for plain conversational turns and all
   * user messages — see {@link MessageTrace}.
   */
  trace?: MessageTrace;
}

/** Streaming state surfaced by a ChatHook while a response is in flight. */
export interface ChatStreamingState {
  status:
    | 'idle'
    | 'connecting'
    | 'streaming'
    | 'thinking'
    | 'complete'
    | 'error'
    | 'aborted';
  content: string;
  thinking: string;
  isStreaming: boolean;
}
