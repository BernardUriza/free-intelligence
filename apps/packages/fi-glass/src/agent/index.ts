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
  type TurnError,
  type AppHandledError,
  DEFAULT_TURN_TIMEOUT_MS,
} from './useAgentConversation';
export {
  AgentConversationSurface,
  type AgentConversationSurfaceProps,
  type AgentConversationSurfaceLayout,
} from './AgentConversationSurface';
// B3-FIGLASS-12: floating jump-to-latest affordance (pin-to-bottom UX).
export {
  ScrollToBottomButton,
  type ScrollToBottomButtonProps,
} from './ScrollToBottomButton';
// FG-4: viewport-locked agent-workspace page primitive (composes a full page
// from slots — header / main / conversation / rail / footer). B3-FIGLASS-MOBILE-1
// folds in an optional sidebar slot + opt-in mobile drawer.
export { AgentWorkspaceShell } from './AgentWorkspaceShell';
export type {
  AgentWorkspaceShellProps,
  AgentWorkspaceShellVisual,
  AgentWorkspaceShellDensity,
  AgentWorkspaceShellApi,
} from './AgentWorkspaceShell';
