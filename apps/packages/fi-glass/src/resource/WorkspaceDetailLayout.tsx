'use client';

/**
 * fi-glass · the two-column detail of a resource workspace.
 *
 * Main column plus a fixed-width rail. Below the mobile breakpoint the rail
 * STACKS under the main column instead of shrinking beside it — a 352px rail
 * next to a conversation on a 390px phone leaves neither one usable, and that is
 * the budget [[mobile-viewport-ux]] exists to defend.
 *
 * The rail is optional. A workspace with nothing to put in it renders the main
 * column full width rather than an empty 352px gutter.
 */

import { type CSSProperties, type ReactNode } from 'react';
import {
  FI_DETAIL_CLASS,
  FI_DETAIL_MAIN_CLASS,
  FI_DETAIL_RAIL_CLASS,
  useResourceStyle,
} from './resourceStyle';

export interface WorkspaceDetailLayoutProps {
  children: ReactNode;
  /** The rail's content. Omit for a single-column workspace. */
  rail?: ReactNode;
  /** Rail width on desktop (number → px). Default 352. */
  railWidth?: number | string;
  /** Accessible label for the rail's complementary landmark. */
  railLabel?: string;
  className?: string;
}

export function WorkspaceDetailLayout({
  children,
  rail,
  railWidth,
  railLabel,
  className,
}: WorkspaceDetailLayoutProps) {
  useResourceStyle();
  const style =
    railWidth != null
      ? ({
          ['--fi-resource-rail-width' as string]:
            typeof railWidth === 'number' ? `${railWidth}px` : railWidth,
        } as CSSProperties)
      : undefined;
  return (
    <div
      className={className ? `${FI_DETAIL_CLASS} ${className}` : FI_DETAIL_CLASS}
      style={style}
    >
      <div className={FI_DETAIL_MAIN_CLASS}>{children}</div>
      {rail != null && (
        <aside className={FI_DETAIL_RAIL_CLASS} aria-label={railLabel}>
          {rail}
        </aside>
      )}
    </div>
  );
}
