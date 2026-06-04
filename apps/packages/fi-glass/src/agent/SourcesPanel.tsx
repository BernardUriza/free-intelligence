'use client';

import { resolveIcons, type AgentIconSet } from './icons';
import type { AgentClassNames } from './types';

export interface SourcesPanelProps {
  /** Evidence references (e.g. source URLs). Contract field name = `sources`. */
  sources: string[];
  classNames?: AgentClassNames;
  icons?: Partial<AgentIconSet>;
  /** Header label (default "Sources"). */
  label?: string;
}

/** Split a URL into `{host, rest}` so the host bolds and the path dims — sources
 * are more legible when the eye lands on the domain first. Falls back gracefully
 * on a non-URL string (e.g. an internal corpus id from a RAG flow). */
function splitSource(url: string): { host: string; rest: string } {
  try {
    const u = new URL(url);
    const host = u.host.replace(/^www\./, '');
    const rest = `${u.pathname}${u.search}${u.hash}`;
    return { host, rest: rest === '/' ? '' : rest };
  } catch {
    return { host: url, rest: '' };
  }
}

/**
 * The Sources panel — the references the agent actually fetched/cited. fi-glass
 * ships a neutral default; an app with branded styling (e.g. insult_ai's Bright
 * Data receipts) can pass its row class via `classNames.sourceRow`, or replace
 * this whole panel through the AgentPanel's `renderSources` slot.
 */
export function SourcesPanel({
  sources,
  classNames,
  icons,
  label = 'Sources',
}: SourcesPanelProps) {
  if (sources.length === 0) return null;
  const ic = resolveIcons(icons);
  const SourcesIcon = ic.sources;
  const ExternalIcon = ic.external;
  const card = classNames?.card ?? '';
  const hint = classNames?.hint ?? '';
  const row =
    classNames?.sourceRow ??
    'bg-zinc-500/10 hover:border-zinc-400/40 hover:bg-zinc-500/20';

  return (
    <div className={`${card} text-sm`.trim()}>
      <h2 className="mb-3 inline-flex items-center gap-2 font-medium text-zinc-200">
        <SourcesIcon className="h-4 w-4 text-zinc-400" aria-hidden />
        {label}
        <span className={`${hint} ml-1 text-xs tabular-nums`.trim()}>
          ({sources.length})
        </span>
      </h2>
      <ul className="flex flex-col gap-1.5 text-sm">
        {sources.map((u) => {
          const { host, rest } = splitSource(u);
          return (
            <li key={u}>
              <a
                href={u}
                target="_blank"
                rel="noopener noreferrer"
                className={`group flex items-center gap-2 rounded-lg border border-transparent px-3 py-2 transition ${row}`}
              >
                <span className="truncate">
                  <span className="font-semibold text-zinc-100">{host}</span>
                  {rest && (
                    <span className="ml-0.5 font-mono text-xs text-zinc-500">
                      {rest}
                    </span>
                  )}
                </span>
                <ExternalIcon
                  className="ml-auto h-3.5 w-3.5 shrink-0 text-zinc-400 opacity-0 transition group-hover:opacity-100"
                  aria-hidden
                />
              </a>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
