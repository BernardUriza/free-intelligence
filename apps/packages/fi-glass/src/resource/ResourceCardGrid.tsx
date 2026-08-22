'use client';

/**
 * fi-glass · the card grid of a resource index, and the card itself.
 *
 * A semantic `<ul>` of `<li>` — not a pile of divs — so a screen reader can
 * announce how many resources there are and move between them. `grid-auto-rows:
 * 1fr` keeps every card in a row the same height, which is why the description
 * clamps at three lines instead of stretching its neighbours.
 *
 * The card renders as an `<a>` when given `href` and a `<button>` otherwise. That
 * is not cosmetic: a real link is middle-clickable, openable in a new tab, and
 * shows its target in the status bar — everything a div-with-onClick throws away.
 */

import { type ReactNode } from 'react';
import { withTouchTarget } from '../shell/touchTarget';
import {
  FI_CARD_CLASS,
  FI_CARD_DESC_CLASS,
  FI_CARD_GRID_CLASS,
  FI_CARD_META_CLASS,
  FI_CARD_TITLE_CLASS,
  useResourceStyle,
} from './resourceStyle';

export interface ResourceCardProps {
  title: string;
  /** Clamped to three lines. Omit (or empty) and the row simply is not rendered. */
  description?: string;
  /** Already-formatted, e.g. "Updated 6 days ago" — fi-glass does no i18n or relative time. */
  meta?: ReactNode;
  /** Renders a real anchor. Without it the card is a button. */
  href?: string;
  onClick?: () => void;
  className?: string;
}

export function ResourceCard({
  title,
  description,
  meta,
  href,
  onClick,
  className,
}: ResourceCardProps) {
  useResourceStyle();
  const body = (
    <>
      <span className={FI_CARD_TITLE_CLASS}>{title}</span>
      {description ? <span className={FI_CARD_DESC_CLASS}>{description}</span> : null}
      {meta != null ? <span className={FI_CARD_META_CLASS}>{meta}</span> : null}
    </>
  );
  const classes = withTouchTarget(className ? `${FI_CARD_CLASS} ${className}` : FI_CARD_CLASS);
  if (href) {
    return (
      <a className={classes} href={href} onClick={onClick}>
        {body}
      </a>
    );
  }
  return (
    <button type="button" className={classes} onClick={onClick}>
      {body}
    </button>
  );
}

export interface ResourceCardGridProps {
  /** One `<li>` per child. Pass {@link ResourceCard}s. */
  children: ReactNode[];
  /** Rendered INSTEAD of the grid when there are no children. */
  emptyState?: ReactNode;
  /** Required: the list needs a name for the same reason the search box does. */
  ariaLabel: string;
  className?: string;
}

export function ResourceCardGrid({
  children,
  emptyState,
  ariaLabel,
  className,
}: ResourceCardGridProps) {
  useResourceStyle();
  const items = children.filter(Boolean);
  if (items.length === 0 && emptyState != null) return <>{emptyState}</>;
  return (
    <ul
      className={className ? `${FI_CARD_GRID_CLASS} ${className}` : FI_CARD_GRID_CLASS}
      aria-label={ariaLabel}
    >
      {items.map((child, i) => (
        <li key={i}>{child}</li>
      ))}
    </ul>
  );
}
