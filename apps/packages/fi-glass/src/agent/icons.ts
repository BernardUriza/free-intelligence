/**
 * AgentIconSet — the icons the agent panels need, with lucide defaults.
 *
 * Icons are injectable per panel (the `icons` prop merges over these defaults),
 * so an app can swap the icon language without forking the components. The tool
 * map is keyed by visual category (see toolClassify), not lucide names, so a
 * swap is a one-line change here.
 */

import {
  AlertTriangle,
  BookOpen,
  Bot,
  ExternalLink,
  FileText,
  Globe,
  ListChecks,
  Loader2,
  Receipt,
  Search,
  Terminal,
  Wrench,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { classifyTool, type ToolCategory } from './toolClassify';

export interface AgentIconSet {
  /** Plan checklist header. */
  plan: LucideIcon;
  /** Guard/warning indicator. */
  warning: LucideIcon;
  /** In-progress spinner (e.g. the "still working" banner). Spun via animate-spin. */
  spinner: LucideIcon;
  /** Assistant identity (Steps panel header). */
  bot: LucideIcon;
  /** Sources panel header. */
  sources: LucideIcon;
  /** Outgoing-link arrow on each source row. */
  external: LucideIcon;
  /** Per-category tool icons for the Steps audit trail. */
  tools: Record<ToolCategory, LucideIcon>;
}

export const defaultAgentIcons: AgentIconSet = {
  plan: ListChecks,
  warning: AlertTriangle,
  spinner: Loader2,
  bot: Bot,
  sources: Receipt,
  external: ExternalLink,
  tools: {
    search: Search,
    scrape: FileText,
    browser: Globe,
    rag: BookOpen,
    bash: Terminal,
    introspect: ListChecks,
    generic: Wrench,
  },
};

/** Merge caller overrides over the defaults (deep-merges the `tools` map). */
export function resolveIcons(overrides?: Partial<AgentIconSet>): AgentIconSet {
  if (!overrides) return defaultAgentIcons;
  return {
    ...defaultAgentIcons,
    ...overrides,
    tools: { ...defaultAgentIcons.tools, ...(overrides.tools ?? {}) },
  };
}

/** Resolve the icon for a raw tool name via its category. */
export function toolIcon(icons: AgentIconSet, name: string): LucideIcon {
  return icons.tools[classifyTool(name)];
}
