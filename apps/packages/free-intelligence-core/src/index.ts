// @free-intelligence/core — public surface.
// Phase 1 ships the theme-token contract. Berkelio (97) adds the agent event
// contract (Plan/Steps/Sources/Guard) below, material-agnostic; the fi-runner
// stream client lands in a later phase.
export type { ThemeTokens } from './theme/contract';
export type {
  VoiceAdapter,
  VoiceOption,
  AudioSource,
  TranscriptResult,
  TranscribeContext,
} from './voice/adapter';
export type { ChatMessage, ChatStreamingState } from './chat/message';
export type { ChatHook } from './chat/hook';

// Agent-turn contract (Berkelio). Types describe the wire stream + reduced
// state; the reducer + state factory are pure runtime values.
export type {
  AgentStreamEvent,
  StepStatus,
  GuardLevel,
  ToolCall,
  GuardRejection,
  AgentMeta,
} from './agent/events';
export type {
  PlanStep,
  AgentPlan,
  PlanOutcome,
  AgentTurnStatus,
  AgentTurnState,
} from './agent/state';
export { initialAgentTurnState, applyAgentEvent } from './agent/state';
export type { AgentHook } from './agent/hook';
