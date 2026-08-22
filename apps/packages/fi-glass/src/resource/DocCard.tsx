'use client';

/**
 * fi-glass · the small card for one document in a rail's knowledge panel, and
 * the two-column grid they sit in.
 *
 * Deliberately not a `ResourceCard` in miniature: this one clamps its title at
 * two lines, pins its meta to the bottom so a grid row stays even, and carries a
 * type badge. Forcing both through one component would mean a `variant` prop
 * that reads as configuration and behaves as two components.
 */

import { type ReactNode } from 'react';
import { withTouchTarget } from '../shell/touchTarget';
import {
  FI_DOC_CARD_BADGE_CLASS,
  FI_DOC_CARD_CLASS,
  FI_DOC_CARD_META_CLASS,
  FI_DOC_CARD_TITLE_CLASS,
  FI_DOC_GRID_CLASS,
  useResourceStyle,
} from './resourceStyle';

export interface DocCardProps {
  title: string;
  /** Already formatted, e.g. "67 lines" / "4 chunks". */
  meta?: ReactNode;
  /** Short type marker, e.g. "TEXT". Rendered uppercase by the stylesheet. */
  badge?: string;
  onClick?: () => void;
  className?: string;
}

export function DocCard({ title, meta, badge, onClick, className }: DocCardProps) {
  useResourceStyle();
  return (
    <button
      type="button"
      className={withTouchTarget(
        className ? `${FI_DOC_CARD_CLASS} ${className}` : FI_DOC_CARD_CLASS,
      )}
      onClick={onClick}
      title={title}
    >
      {badge ? <span className={FI_DOC_CARD_BADGE_CLASS}>{badge}</span> : null}
      <span className={FI_DOC_CARD_TITLE_CLASS}>{title}</span>
      {meta != null ? <span className={FI_DOC_CARD_META_CLASS}>{meta}</span> : null}
    </button>
  );
}

export interface DocCardGridProps {
  children: ReactNode[];
  emptyState?: ReactNode;
  ariaLabel: string;
  className?: string;
}

export function DocCardGrid({ children, emptyState, ariaLabel, className }: DocCardGridProps) {
  useResourceStyle();
  const items = children.filter(Boolean);
  if (items.length === 0 && emptyState != null) return <>{emptyState}</>;
  return (
    <ul
      className={className ? `${FI_DOC_GRID_CLASS} ${className}` : FI_DOC_GRID_CLASS}
      aria-label={ariaLabel}
    >
      {items.map((child, i) => (
        <li key={i}>{child}</li>
      ))}
    </ul>
  );
}
