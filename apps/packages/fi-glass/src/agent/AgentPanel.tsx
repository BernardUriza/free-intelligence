'use client';

import type { ReactNode } from 'react';
import type { AgentTurnState, GuardRejection } from '@free-intelligence/core';
import { PlanChecklist } from './PlanChecklist';
import { StepsPanel } from './StepsPanel';
import { SourcesPanel } from './SourcesPanel';
import type { AgentIconSet } from './icons';
import type { AgentClassNames } from './types';

export interface AgentPanelProps {
  /**
   * The reduced state of one agentic turn (built by core's `applyAgentEvent`).
   * Passed directly — NOT via the AgentHook — because consumers render a panel
   * per historical turn/message, and the hook models only the current turn.
   * A single-turn app simply passes `agentHook.turn`.
   */
  turn: AgentTurnState;
  /** Optional target (URL/claim) for the Steps live label. */
  target?: string;
  classNames?: AgentClassNames;
  icons?: Partial<AgentIconSet>;
  enableSlowBanner?: boolean;
  slowThresholdMs?: number;
  /** Replace the default Sources panel (e.g. an app's branded source list). */
  renderSources?: (sources: string[]) => ReactNode;
  /** Override the guard-rejection banner (copy is app-owned). */
  renderGuardBanner?: (rejection: GuardRejection) => ReactNode;
}

/**
 * The glass-box agentic panel: Plan (contract, guard woven in) + Steps (live
 * audit trail) + Sources (evidence). Each sub-panel self-hides when it has
 * nothing to show, so an early/no-tool turn degrades gracefully.
 */
export function AgentPanel({
  turn,
  target,
  classNames,
  icons,
  enableSlowBanner,
  slowThresholdMs,
  renderSources,
  renderGuardBanner,
}: AgentPanelProps) {
  return (
    <>
      <PlanChecklist
        plan={turn.plan}
        classNames={classNames}
        icons={icons}
        renderGuardBanner={renderGuardBanner}
      />
      <StepsPanel
        steps={turn.steps}
        status={turn.status}
        target={target}
        classNames={classNames}
        icons={icons}
        enableSlowBanner={enableSlowBanner}
        slowThresholdMs={slowThresholdMs}
      />
      {renderSources ? (
        renderSources(turn.sources)
      ) : (
        <SourcesPanel sources={turn.sources} classNames={classNames} icons={icons} />
      )}
    </>
  );
}
