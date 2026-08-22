'use client';

/**
 * fi-glass · the stacked panels of a workspace rail.
 *
 * `RailPanelStack` draws the bordered, rounded container; `RailPanel` is one
 * section inside it, with a head (title + actions) over its body. Dividers come
 * from an adjacency rule, not from a prop the consumer has to get right — the
 * first panel is never asked to know it is first.
 */

import { type ReactNode } from 'react';
import {
  FI_RAIL_PANEL_CLASS,
  FI_RAIL_PANEL_HEAD_CLASS,
  FI_RAIL_PANEL_TITLE_CLASS,
  FI_RAIL_STACK_CLASS,
  useResourceStyle,
} from './resourceStyle';

export interface RailPanelProps {
  /** A string is wrapped in the title slot; a node is used as-is. */
  title: ReactNode;
  children?: ReactNode;
  /** Controls rendered at the end of the head row (e.g. add / search). */
  actionSlot?: ReactNode;
  className?: string;
}

export function RailPanel({ title, children, actionSlot, className }: RailPanelProps) {
  useResourceStyle();
  return (
    <section className={className ? `${FI_RAIL_PANEL_CLASS} ${className}` : FI_RAIL_PANEL_CLASS}>
      <div className={FI_RAIL_PANEL_HEAD_CLASS}>
        {typeof title === 'string' ? (
          <span className={FI_RAIL_PANEL_TITLE_CLASS}>{title}</span>
        ) : (
          title
        )}
        {actionSlot}
      </div>
      {children}
    </section>
  );
}

export interface RailPanelStackProps {
  children: ReactNode;
  className?: string;
}

export function RailPanelStack({ children, className }: RailPanelStackProps) {
  useResourceStyle();
  return (
    <div className={className ? `${FI_RAIL_STACK_CLASS} ${className}` : FI_RAIL_STACK_CLASS}>
      {children}
    </div>
  );
}
