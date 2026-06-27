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
export type { ChatMessage, ChatStreamingState, MessageTrace } from './chat/message';
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
export { makeUserMessage, foldAssistantTurn } from './agent/transcript';
export type { AgentHook, AgentSendMeta } from './agent/hook';

// Conversation library contract (DD-002B1). Local-first transcript persistence:
// record/summary types, the ConversationLibrary storage contract, and pure
// helpers (title/preview derivation + privacy-by-structure sanitization).
// Storage adapters (IndexedDB, backend) implement the contract in later layers.
export type {
  ConversationRecord,
  ConversationSummary,
  ConversationLibrary,
  CreateConversationRecordArgs,
} from './conversation';
export {
  CONVERSATION_SCHEMA_VERSION,
  createConversationRecord,
  summarizeConversation,
  deriveConversationTitle,
  deriveConversationPreview,
  resolveConversationTitle,
  renameConversationRecord,
  sanitizeConversationMessage,
} from './conversation';
