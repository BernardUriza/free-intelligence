/**
 * Tool classification + live-status helpers for the Steps audit trail.
 *
 * Pure and generic — a raw tool name like `mcp__brightdata__scrape_as_markdown`
 * or `Bash` → a visual category + a short display name + a live status. No app
 * deps, no icons (the icon set maps a category → a component separately).
 */

import type { ToolCall } from '@free-intelligence/core';

export type ToolCategory =
  | 'search'
  | 'scrape'
  | 'browser'
  | 'rag'
  | 'bash'
  | 'introspect'
  | 'generic';

/** Classify a raw tool name into a visual category (loose substring match, so a
 * rename like `scrape_as_markdown` → `scrape_markdown` still resolves). */
export function classifyTool(name: string): ToolCategory {
  const n = name.toLowerCase();
  if (n.includes('search')) return 'search';
  if (n.includes('scrape') || n.includes('fetch') || n.includes('unlock')) return 'scrape';
  if (n.includes('browser')) return 'browser';
  if (n.includes('document') || n.includes('rag')) return 'rag';
  if (n === 'bash' || n.endsWith('__bash')) return 'bash';
  if (n.includes('listmcp') || n.includes('listtool')) return 'introspect';
  return 'generic';
}

/** Strip the `mcp__<server>__` prefix for display (`scrape_as_markdown`). */
export function shortToolName(name: string): string {
  return name.replace(/^mcp__[^_]+__/, '');
}

export type ToolVisualStatus = 'active' | 'sent' | 'done' | 'error';

/** Resolve a tri-state `isError` to a coarse status. null = still in flight. */
function stepStatusKey(isError: boolean | null): 'pending' | 'done' | 'error' {
  if (isError === null) return 'pending';
  return isError ? 'error' : 'done';
}

/** Index of the latest still-open (pending) tool — the one to highlight live. */
export function latestOpenToolIndex(steps: ToolCall[]): number {
  return steps.reduce(
    (latest, step, index) => (step.isError === null ? index : latest),
    -1
  );
}

/** Visual status for one step: only the latest open step reads "active". */
export function toolVisualStatus(
  step: ToolCall,
  index: number,
  latestOpenIndex: number,
  live: boolean
): ToolVisualStatus {
  const raw = stepStatusKey(step.isError);
  if (raw === 'error') return 'error';
  if (raw === 'done') return 'done';
  if (!live) return 'done';
  return index === latestOpenIndex ? 'active' : 'sent';
}
