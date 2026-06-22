'use client';

import { useEffect, useState } from 'react';
import type { AgentTurnStatus, ToolCall } from '@free-intelligence/core';
import { resolveIcons, toolIcon, type AgentIconSet } from './icons';
import { latestOpenToolIndex, shortToolName, toolVisualStatus } from './toolClassify';
import type { AgentClassNames } from './types';

export interface StepsPanelProps {
  steps: ToolCall[];
  status: AgentTurnStatus;
  /** Optional target (URL/claim) the agent is working on, for the live label. */
  target?: string;
  classNames?: AgentClassNames;
  icons?: Partial<AgentIconSet>;
  /** Show the "still working" reassurance banner past the threshold (default true). */
  enableSlowBanner?: boolean;
  /** Milliseconds before the slow banner appears (default 12s). */
  slowThresholdMs?: number;
}

/**
 * Collapsible audit trail that lists every tool call as it happens. Auto-expands
 * while the turn is live and collapses on done. The "thinking" status is generic
 * here — fi-glass knows nothing about clinical/roast modes; the slow banner is a
 * plain prop (apps that have their own slow UI pass enableSlowBanner={false}).
 */
export function StepsPanel({
  steps,
  status,
  target,
  classNames,
  icons,
  enableSlowBanner = true,
  slowThresholdMs = 12_000,
}: StepsPanelProps) {
  const ic = resolveIcons(icons);
  const BotIcon = ic.bot;
  const SpinnerIcon = ic.spinner;
  const card = classNames?.card ?? '';
  const hint = classNames?.hint ?? '';

  const live = status === 'thinking' || status === 'streaming';
  const [openOverride, setOpenOverride] = useState<boolean | null>(null);
  const open = openOverride ?? live;

  const [elapsed, setElapsed] = useState(0);
  useEffect(() => {
    if (!live || !enableSlowBanner) {
      setElapsed(0);
      return;
    }
    const start = Date.now();
    const t = setInterval(() => setElapsed(Date.now() - start), 500);
    return () => clearInterval(t);
  }, [live, enableSlowBanner]);
  const showSlowBanner = live && enableSlowBanner && elapsed >= slowThresholdMs;

  if (steps.length === 0 && status === 'done') return null;

  const shortTarget =
    target && target.length > 36 ? `${target.slice(0, 33).trim()}…` : target;

  const summary =
    status === 'thinking'
      ? shortTarget
        ? `Unlocking ${shortTarget}…`
        : 'thinking…'
      : status === 'streaming' && steps.length === 0
        ? 'writing…'
        : `${steps.length} ${steps.length === 1 ? 'step' : 'steps'}`;
  const latestPendingIndex = live ? latestOpenToolIndex(steps) : -1;

  return (
    <div className={`${card} mb-2 text-sm`.trim()}>
      <button
        type="button"
        onClick={() => setOpenOverride(!open)}
        className="flex w-full items-center justify-between gap-2 text-left text-zinc-300 hover:text-zinc-100"
        aria-expanded={open}
      >
        <span className="inline-flex items-center gap-2 font-medium">
          <BotIcon className="h-4 w-4 text-zinc-400" aria-hidden />
          {summary}
        </span>
        <span className={`${hint} text-xs`.trim()}>{open ? 'hide' : 'show'}</span>
      </button>
      {showSlowBanner && (
        <div
          className="mt-2 inline-flex items-center gap-2 rounded-lg border border-sky-700/40 bg-sky-950/30 p-2.5 text-xs text-sky-200"
          role="status"
          aria-live="polite"
        >
          <SpinnerIcon
            className="h-3.5 w-3.5 shrink-0 animate-spin text-sky-400"
            aria-hidden
          />
          <span>Still working. This can take a second.</span>
        </div>
      )}
      {open && steps.length > 0 && (
        <ol className="mt-2 space-y-1">
          {steps.map((s, i) => {
            const ToolIcon = toolIcon(ic, s.name);
            const statusKey = toolVisualStatus(s, i, latestPendingIndex, live);
            const errored = statusKey === 'error';
            const active = statusKey === 'active';
            return (
              <li
                key={s.id ?? `${s.name}-${i}`}
                className={`flex items-center gap-2 font-mono text-xs ${
                  errored ? 'text-red-400' : 'text-zinc-400'
                }`}
              >
                <ToolIcon className="h-3.5 w-3.5 shrink-0" aria-hidden />
                <span className="truncate">{shortToolName(s.name)}</span>
                {s.server && s.server !== 'brightdata' && (
                  <span className={`${hint} text-[10px] uppercase`.trim()}>
                    · {s.server}
                  </span>
                )}
                <span
                  className={`ml-auto rounded-full border px-1.5 py-0.5 text-[9px] uppercase tracking-wide ${
                    active
                      ? 'border-amber-400/30 bg-amber-400/10 text-amber-300'
                      : statusKey === 'sent'
                        ? 'border-zinc-500/25 bg-zinc-500/10 text-zinc-400'
                        : errored
                          ? 'border-red-400/30 bg-red-400/10 text-red-300'
                          : 'border-emerald-400/25 bg-emerald-400/10 text-emerald-300'
                  }`}
                  aria-label={statusKey}
                >
                  {statusKey}
                </span>
              </li>
            );
          })}
        </ol>
      )}
    </div>
  );
}
