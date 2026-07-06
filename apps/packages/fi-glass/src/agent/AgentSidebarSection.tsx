'use client';

/**
 * fi-glass · sidebar section primitive (B3-FIGLASS-SHELL-PRIMITIVES-1C).
 *
 * The labelled group that holds a list of {@link AgentSidebarItem} rows: a header
 * (title + an action affordance) over either the rows or an empty state. og118
 * hand-wrote this header twice (`og-sidebar-head` for conversations,
 * `og-projects-head` for projects — structural twins per the audit); this lifts
 * the *anatomy* (the head layout, the count→empty gate) into the framework so
 * og118/slate/paper render a sidebar section without re-authoring the skeleton.
 *
 * The framework owns the header layout and the empty gate; the consumer owns the
 * *meaning* — the section title copy/branding, the action button copy, the list
 * of rows, and the empty-state message. Deliberately free of product nouns
 * (no `projectCount`, `newProjectLabel`, `conversationCount`): those live in the
 * consumer and reach the section through the generic slots below.
 */

import { type CSSProperties, type ReactNode } from 'react';
import {
  FI_SIDEBAR_SECTION_CLASS,
  FI_SECTION_HEAD_CLASS,
  FI_SECTION_TITLE_CLASS,
  FI_SECTION_CARD_CLASS,
  FI_SECTION_FOOTER_CLASS,
  FI_SECTION_SCROLL_CLASS,
  useSidebarSectionStyle,
} from './sidebarSectionStyle';

function joinClasses(...parts: (string | false | null | undefined)[]): string {
  return parts.filter(Boolean).join(' ');
}

export interface AgentSidebarSectionProps {
  /** A plain string is wrapped in the title slot; a node (e.g. branded markup) is used as-is. */
  title: ReactNode;
  /** The rows (e.g. a `<nav>` of {@link AgentSidebarItem}). Shown when `count > 0`. */
  children: ReactNode;
  /** Header action affordance rendered at the end of the head row (e.g. a "+ Nuevo" button). */
  actionSlot?: ReactNode;
  /** Shown instead of `children` when `count === 0`. Omit to always render `children`. */
  emptyState?: ReactNode;
  /** Number of rows; gates whether `emptyState` (0) or `children` (>0) renders. */
  count: number;
  /** Replaces the default head (title + actionSlot) entirely when the consumer needs a custom header. */
  headerSlot?: ReactNode;
  /**
   * Distribution variant. `"plain"` (default) is the original borderless section —
   * unchanged for existing consumers. `"card"` wraps the section in a padded,
   * bordered, rounded card (token-driven via `--fi-section-card-*` + `--fi-radius-section`)
   * so a sidebar group reads as a distinct surface with breathing room.
   */
  variant?: 'plain' | 'card';
  /**
   * Content rendered BELOW the rows/empty-state, separated by a divider + gap (e.g.
   * an upload dropzone that must not collide with the list). Omit for no footer.
   */
  footerSlot?: ReactNode;
  /**
   * How the rows region sizes. `"none"` (default) lets the rows take their natural
   * height (the original behavior). `"content"` wraps the rows in a content-aware
   * scroll region: they grow by content and only scroll past `maxBlockSize` — a
   * rem-based cap, NOT a viewport `vh` that crushes a few rows on short screens.
   */
  scrollBehavior?: 'none' | 'content';
  /**
   * The scroll cap for `scrollBehavior="content"` (number → px). Default `18rem`
   * (~6 rows). Sets the `--fi-section-scroll-max` token on the scroll region.
   */
  maxBlockSize?: number | string;
  /** Accessible label for the section element. */
  ariaLabel?: string;
  className?: string;
}

export function AgentSidebarSection({
  title,
  children,
  actionSlot,
  emptyState,
  count,
  headerSlot,
  variant = 'plain',
  footerSlot,
  scrollBehavior = 'none',
  maxBlockSize,
  ariaLabel,
  className,
}: AgentSidebarSectionProps) {
  useSidebarSectionStyle();
  const titleNode =
    typeof title === 'string' ? (
      <span className={FI_SECTION_TITLE_CLASS}>{title}</span>
    ) : (
      title
    );
  const showEmpty = count === 0 && emptyState != null;
  const body = showEmpty ? emptyState : children;
  const scrollStyle =
    maxBlockSize != null
      ? ({
          ['--fi-section-scroll-max' as string]:
            typeof maxBlockSize === 'number' ? `${maxBlockSize}px` : maxBlockSize,
        } as CSSProperties)
      : undefined;
  return (
    <section
      className={joinClasses(
        FI_SIDEBAR_SECTION_CLASS,
        variant === 'card' && FI_SECTION_CARD_CLASS,
        className,
      )}
      aria-label={ariaLabel}
    >
      {headerSlot ?? (
        <div className={FI_SECTION_HEAD_CLASS}>
          {titleNode}
          {actionSlot}
        </div>
      )}
      {scrollBehavior === 'content' && !showEmpty ? (
        <div className={FI_SECTION_SCROLL_CLASS} style={scrollStyle}>
          {body}
        </div>
      ) : (
        body
      )}
      {footerSlot != null && <div className={FI_SECTION_FOOTER_CLASS}>{footerSlot}</div>}
    </section>
  );
}
