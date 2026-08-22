'use client';

/**
 * fi-glass · the header of a resource INDEX page.
 *
 * Title on the left; sort control and primary CTA on the right. The framework
 * owns that layout and its wrapping behaviour; the consumer owns every word and
 * both controls — this component renders no button of its own, so it can never
 * acquire an opinion about what the resource is called or how it sorts.
 */

import { type ReactNode } from 'react';
import {
  FI_INDEX_ACTIONS_CLASS,
  FI_INDEX_HEADER_CLASS,
  FI_INDEX_TITLE_CLASS,
  useResourceStyle,
} from './resourceStyle';

export interface ResourceIndexHeaderProps {
  /** A string is wrapped in the title slot; a node is used as-is (branded markup). */
  title: ReactNode;
  /** Sort affordance (a select, a menu trigger) — rendered before the CTA. */
  sortSlot?: ReactNode;
  /** The primary call to action (e.g. "New …"). */
  actionSlot?: ReactNode;
  className?: string;
}

export function ResourceIndexHeader({
  title,
  sortSlot,
  actionSlot,
  className,
}: ResourceIndexHeaderProps) {
  useResourceStyle();
  return (
    <header className={className ? `${FI_INDEX_HEADER_CLASS} ${className}` : FI_INDEX_HEADER_CLASS}>
      {typeof title === 'string' ? <h1 className={FI_INDEX_TITLE_CLASS}>{title}</h1> : title}
      {(sortSlot || actionSlot) && (
        <div className={FI_INDEX_ACTIONS_CLASS}>
          {sortSlot}
          {actionSlot}
        </div>
      )}
    </header>
  );
}
