'use client';

import type { ReactNode } from 'react';
import type { AgentPlan, GuardRejection } from '@free-intelligence/core';
import { resolveIcons, type AgentIconSet } from './icons';
import type { AgentClassNames } from './types';

export interface PlanChecklistProps {
  plan: AgentPlan | null;
  classNames?: AgentClassNames;
  icons?: Partial<AgentIconSet>;
  /**
   * Override the guard-rejection banner. The guard is a QUALITY woven into the
   * plan, not a separate widget — when a rejection is present this renders it.
   * The default copy is generic ("A guard blocked this plan"); apps that want
   * their own wording (e.g. "PlanGuard blocked this plan") pass this slot.
   */
  renderGuardBanner?: (rejection: GuardRejection) => ReactNode;
}

/**
 * The agent's plan-of-action as a live checklist. Renders only when a plan was
 * declared. Visual rule: signal > detail — this says WHAT the agent committed
 * to; the Steps panel shows every tool call as it happens.
 */
export function PlanChecklist({
  plan,
  classNames,
  icons,
  renderGuardBanner,
}: PlanChecklistProps) {
  if (!plan || plan.steps.length === 0) return null;

  const ic = resolveIcons(icons);
  const PlanIcon = ic.plan;
  const WarnIcon = ic.warning;
  const card = classNames?.card ?? '';
  const hint = classNames?.hint ?? '';

  const done = plan.steps.filter((s) => s.status === 'done').length;
  const total = plan.steps.length;
  const rejection = plan.rejection ?? null;
  const matchedIndexes = new Set(rejection?.matched.map((m) => m.index) ?? []);

  // Terminal plan verdict (finalize_plan / cancel_plan) → header badge.
  const outcome = plan.outcome ?? null;
  const outcomeBadge =
    outcome === 'completed'
      ? { label: 'completed', tone: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300' }
      : outcome === 'failed'
        ? { label: 'failed', tone: 'border-red-500/30 bg-red-500/10 text-red-300' }
        : outcome === 'cancelled'
          ? { label: 'cancelled', tone: 'border-zinc-500/30 bg-zinc-500/10 text-zinc-400' }
          : null;
  // The plan was restructured mid-turn (insert_step / replan).
  const amended = plan.amended ?? null;
  const amendedLabel = amended === 'replan' ? 're-planned' : amended === 'insert' ? 'revised' : null;

  return (
    <div className={`${card} mb-2 text-sm`.trim()}>
      <div className="flex items-center justify-between gap-2 text-zinc-300">
        <span className="inline-flex items-center gap-2 font-medium">
          <PlanIcon className="h-4 w-4 text-zinc-400" aria-hidden />
          plan
          {amendedLabel && (
            <span className="rounded border border-amber-500/30 bg-amber-500/10 px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-amber-300">
              {amendedLabel}
            </span>
          )}
          {outcomeBadge && (
            <span className={`rounded border px-1.5 py-0.5 text-[10px] uppercase tracking-wide ${outcomeBadge.tone}`}>
              {outcomeBadge.label}
            </span>
          )}
        </span>
        <span className={`${hint} text-xs tabular-nums`.trim()}>
          {done} / {total}
        </span>
      </div>
      {rejection &&
        (renderGuardBanner ? (
          renderGuardBanner(rejection)
        ) : (
          <div className="mt-2 flex items-start gap-2 rounded border border-amber-500/30 bg-amber-500/10 p-2 text-xs text-amber-200">
            <WarnIcon
              className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-400"
              aria-hidden
            />
            <div className="flex flex-col gap-0.5">
              <span className="font-medium">A guard blocked this plan</span>
              <span className="text-amber-200/80">{rejection.reason}</span>
              {rejection.guard && (
                <span
                  className={`${hint} text-[10px] uppercase tracking-wide text-amber-300/60`.trim()}
                >
                  guard: {rejection.guard}
                </span>
              )}
            </div>
          </div>
        ))}
      <ol className="mt-2 space-y-1.5">
        {plan.steps.map((step, i) => {
          const isRunning = step.status === 'running';
          const isPending = step.status === 'pending';
          const isDone = step.status === 'done';
          const isFailed = step.status === 'failed';
          const isCancelled = step.status === 'cancelled';
          const isRejected = matchedIndexes.has(i);
          const labelTone = isRejected
            ? 'text-amber-300 line-through decoration-amber-500/60'
            : isFailed
              ? 'text-red-400'
              : isCancelled
                ? 'text-zinc-500 line-through decoration-zinc-600'
                : isDone
                  ? 'text-zinc-300'
                  : isRunning
                    ? 'text-zinc-100'
                    : 'text-zinc-500';
          const railTone = isFailed
            ? 'text-red-400'
            : isCancelled
              ? 'text-zinc-500 bg-zinc-500'
              : isDone
                ? 'text-emerald-400 bg-emerald-400'
                : isRunning
                  ? 'text-amber-300 bg-amber-300'
                  : 'text-zinc-600 bg-zinc-700';
          return (
            <li key={i} className="flex flex-col gap-0.5">
              <div className="flex items-center gap-2 text-xs">
                <span
                  className={`h-5 w-1 shrink-0 rounded-full ${railTone} ${
                    isRunning ? 'shadow-[0_0_10px_rgb(251_191_36/0.45)]' : ''
                  }`}
                  aria-label={step.status}
                />
                <span className={`flex-1 truncate ${labelTone}`}>{step.label}</span>
                {isPending && (
                  <span className={`${hint} text-[10px] uppercase tracking-wide`.trim()}>
                    queued
                  </span>
                )}
                {isRunning && (
                  <span className="text-[10px] uppercase tracking-wide text-amber-300">
                    running
                  </span>
                )}
                {isCancelled && (
                  <span className={`${hint} text-[10px] uppercase tracking-wide`.trim()}>
                    cancelled
                  </span>
                )}
              </div>
              {step.summary && isDone && (
                <div className={`${hint} pl-5 font-mono text-[11px] text-zinc-500`.trim()}>
                  {step.summary}
                </div>
              )}
              {step.error && isFailed && (
                <div className="pl-5 font-mono text-[11px] text-red-400/80">
                  {step.error}
                </div>
              )}
              {step.error && isCancelled && (
                <div className="pl-5 font-mono text-[11px] text-zinc-500">
                  {step.error}
                </div>
              )}
              {step.note && (
                <div className="pl-5 text-[11px] italic text-zinc-400">
                  note: {step.note}
                </div>
              )}
            </li>
          );
        })}
      </ol>
    </div>
  );
}
