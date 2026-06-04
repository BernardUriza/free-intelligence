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
