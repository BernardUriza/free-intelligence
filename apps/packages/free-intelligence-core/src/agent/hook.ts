import type { AgentTurnState } from './state';
import type { ChatMessage, MessageImage } from '../chat/message';

/**
 * Per-send metadata the conversation layer may hand the transport. Optional and
 * backward-compatible — a transport that ignores it behaves exactly as before.
 */
export interface AgentSendMeta {
  /**
   * The confirmed conversation so far (prior user/assistant turns, NOT the
   * message being sent). A transport with a stateless/storeless backend replays
   * this for continuity — the og118 canary: the durable transcript lives in the
   * client (IndexedDB), so continuity survives a recycled backend. It is
   * conversational CONTEXT only; the backend re-sanitizes it and never treats it
   * as authorization.
   */
  history?: ChatMessage[];
  /**
   * Images attached to THIS send (OG118-IMAGE-UPLOAD-1) — vision input for the
   * current turn. The transport forwards them to its backend as image content
   * blocks; a transport that ignores `meta` behaves exactly as before.
   */
  images?: MessageImage[];
}

/**
 * AgentHook — the agentic-turn contract the fi-glass agent panels consume.
 *
 * Dependency-inversion spine, twin of ChatHook. The app implements it against
 * its own transport (insult_ai: POST /chat/stream SSE → applyAgentEvent;
 * og118: its own). fi-glass NEVER imports the transport, endpoints, or auth.
 *
 * This is DATA + ACTIONS only. Presentation slots (renderSources /
 * renderGuardBanner / icons) live on the AgentPanel props in fi-glass, NOT here
 * — the hook is data, the panel is render. (Cleaner than Curio's ChatHook, which
 * carried customEmptyState.) Because no member references a UI node type, the
 * hook needs no `TNode` generic; only the panel is generic over its node type.
 */
export interface AgentHook {
  /** Current/last turn's reduced state. */
  turn: AgentTurnState;
  /** Whether a turn is actively streaming. */
  isStreaming: boolean;
  /** Start an agentic turn. `meta.history` lets the conversation layer replay
   * prior turns for continuity on a storeless backend (see {@link AgentSendMeta}). */
  send: (message: string, meta?: AgentSendMeta) => Promise<void>;
  /** Abort the in-flight turn, if supported. */
  abort?: () => void;
  /** Reset the session/turn. */
  reset?: () => void;
}
