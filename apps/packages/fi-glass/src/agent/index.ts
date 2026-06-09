/**
 * fi-glass/agent — the glass-box agentic UI (Berkelio, element 97).
 *
 * Presentational panels that render the agent's Plan (contract, guard woven in),
 * Steps (live tool-call audit trail) and Sources (evidence), driven by the
 * material-agnostic agent contract in @free-intelligence/core. Components take
 * core-typed data directly; the reducer + state live in core (apps map their
 * transport → AgentStreamEvent and reduce with applyAgentEvent).
 */
export { AgentPanel } from './AgentPanel';
export type { AgentPanelProps } from './AgentPanel';
export { PlanChecklist } from './PlanChecklist';
export type { PlanChecklistProps } from './PlanChecklist';
export { StepsPanel } from './StepsPanel';
export type { StepsPanelProps } from './StepsPanel';
export { SourcesPanel } from './SourcesPanel';
export type { SourcesPanelProps } from './SourcesPanel';

export {
  defaultAgentIcons,
  resolveIcons,
  toolIcon,
  type AgentIconSet,
} from './icons';
export {
  classifyTool,
  shortToolName,
  latestOpenToolIndex,
  toolVisualStatus,
  type ToolCategory,
  type ToolVisualStatus,
} from './toolClassify';
export type { AgentClassNames } from './types';

// Agentic conversation (DD-002): transcript + per-turn glass-box, the reusable
// primitive that replaces the consumer-local transcript in og118.
export {
  useAgentConversation,
  type AgentConversation,
  type UseAgentConversationOptions,
} from './useAgentConversation';
export {
  AgentConversationSurface,
  type AgentConversationSurfaceProps,
} from './AgentConversationSurface';
