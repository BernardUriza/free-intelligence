import type { AgentPlan } from '../agent/state';
import type { MessageAuthor, ToolCall } from '../agent/events';

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
  /**
   * The model that actually produced the answer. Provenance, like the plan and
   * the tools — so it lives HERE, not in `metadata`, which persistence drops by
   * design. A "powered by <model>" chip read from `metadata` shows on the live
   * turn and vanishes on reload; read from the trace it survives.
   */
  model?: string;
}

/**
 * MessageImage — one image attached to a user message (OG118-IMAGE-UPLOAD-1).
 *
 * Base64 by design: the shells are local-first (IndexedDB / JSON records), so
 * the bytes ride inside the message instead of referencing a blob store nobody
 * runs. Producers (the composer) downscale before encoding, so a persisted
 * image stays small enough for the conversation-record size caps.
 */
export interface MessageImage {
  /** MIME type of the encoded bytes, e.g. `image/jpeg`, `image/png`. */
  mediaType: string;
  /** Base64-encoded bytes — no `data:` URL prefix. */
  data: string;
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
  /** Which side of the conversation the message sits on. */
  role: 'user' | 'assistant';
  /**
   * WHO said it — the named speaker, not merely the side. A shell with a persona
   * switch (og118's elementos) must attribute each bubble to the persona that
   * actually produced it, and that attribution has to survive a reload, so it is
   * a first-class field (preserved by `sanitizeConversationMessage`, unlike
   * `metadata`). Optional only for messages authored outside the agent contract;
   * everything {@link foldAssistantTurn}/{@link makeUserMessage} builds has one.
   */
  author?: MessageAuthor;
  /** The message text. May be empty on an image-only user message. */
  content: string;
  /**
   * Images attached to this message (user messages only) — rendered in the
   * transcript and sent to the model as vision input. Absent on text-only
   * messages, so the plain case stays byte-identical to before.
   */
  images?: MessageImage[];
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
