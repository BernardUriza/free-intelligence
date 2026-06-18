'use client';

/**
 * AgentWorkspaceShell — the viewport-locked agent-workspace PAGE primitive
 * (FG-4, canary-driven upstream loop, captured by activist-os's FiGlassPrimary).
 *
 * FG-1/FG-2 gave AgentConversationSurface a `layout="contained"` mode so it can
 * live inside a fixed-height cell. But every consumer still hand-rolled the page
 * that wraps it: header + main grid + conversation column + artifact rail +
 * footer, viewport-locked with no page overflow. This primitive composes that
 * page from SLOTS — the next rung toward declarative AgentAppScreen templates.
 *
 * It is pure composition: the conversation is a slot (the app passes its own
 * AgentConversationSurface), not constructed here. Material-agnostic and
 * app-neutral — markers/classes only, no real aurora visual CSS yet.
 */

import type { CSSProperties, ReactNode } from 'react';

export type AgentWorkspaceShellVisual = 'aurora' | 'midnight' | 'clinical';
export type AgentWorkspaceShellDensity = 'compact' | 'comfortable' | 'spacious';

export interface AgentWorkspaceShellProps {
  visual?: AgentWorkspaceShellVisual;
  density?: AgentWorkspaceShellDensity;
  header?: ReactNode;
  conversation: ReactNode;
  rail?: ReactNode;
  footer?: ReactNode;
  className?: string;
  style?: CSSProperties;
}

export function AgentWorkspaceShell({
  visual = 'aurora',
  density = 'comfortable',
  header,
  conversation,
  rail,
  footer,
  className,
  style,
}: AgentWorkspaceShellProps) {
  const rootStyle: CSSProperties = {
    display: 'flex',
    flexDirection: 'column',
    height: '100dvh',
    minHeight: 0,
    overflow: 'hidden',
  };

  const mainStyle: CSSProperties = {
    display: 'grid',
    gridTemplateColumns: rail ? 'minmax(0, 1fr) minmax(280px, 360px)' : 'minmax(0, 1fr)',
    flex: '1 1 auto',
    minHeight: 0,
    overflow: 'hidden',
  };

  const conversationStyle: CSSProperties = { minHeight: 0, overflow: 'hidden' };
  const railStyle: CSSProperties = { minHeight: 0, overflowY: 'auto' };

  const rootClassName = [
    'fi-agent-workspace',
    `fi-visual-${visual}`,
    `fi-density-${density}`,
    className,
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <div
      data-fi-workspace="agent"
      data-fi-visual={visual}
      data-fi-density={density}
      className={rootClassName}
      style={{ ...rootStyle, ...style }}
    >
      {header != null && <div data-fi-slot="header">{header}</div>}
      <div data-fi-slot="main" style={mainStyle}>
        <div data-fi-slot="conversation" style={conversationStyle}>
          {conversation}
        </div>
        {rail != null && (
          <div data-fi-slot="rail" style={railStyle}>
            {rail}
          </div>
        )}
      </div>
      {footer != null && <div data-fi-slot="footer">{footer}</div>}
    </div>
  );
}
