import type { AgentTurnState } from './state';

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
  /** Start an agentic turn. */
  send: (message: string, metadata?: object) => Promise<void>;
  /** Abort the in-flight turn, if supported. */
  abort?: () => void;
  /** Reset the session/turn. */
  reset?: () => void;
}
