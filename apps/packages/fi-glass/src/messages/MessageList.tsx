'use client';

/**
 * fi-glass · MessageList — generic grouped message container.
 *
 * Structure only: it maps pre-grouped items to rows and positions an optional
 * divider per group plus header/footer slots. It owns NO data logic — grouping,
 * streaming rows, typing indicators, and scroll all stay in the app and arrive
 * via slots. Generic over the item type so it never depends on a message shape.
 *
 * CONFIGURABILITY (fire test): the app controls grouping (`groups`), how each
 * item renders (`renderItem`), dividers (`renderDivider`), and everything below
 * the list (`footer`) — without touching fi-glass.
 */

import { type ReactNode } from 'react';

export interface MessageListGroup<T> {
  /** Stable key for the group (also passed to renderDivider). */
  key: string;
  /** Items belonging to this group. */
  items: T[];
}

export interface MessageListProps<T> {
  /** Pre-grouped items (app decides the grouping strategy). */
  groups: MessageListGroup<T>[];
  /** Render a single item. Return value should carry its own React key. */
  renderItem: (item: T, index: number) => ReactNode;
  /** Optional per-group divider (e.g. a date separator). */
  renderDivider?: (key: string) => ReactNode;
  /** Class for the scroll/list container. */
  containerClassName?: string;
  /** Class for each group's inner item wrapper. */
  groupClassName?: string;
  /** Slot rendered before the groups. */
  header?: ReactNode;
  /** Slot rendered after the groups (streaming row, typing dots, spacer…). */
  footer?: ReactNode;
}

export function MessageList<T>({
  groups,
  renderItem,
  renderDivider,
  containerClassName,
  groupClassName,
  header,
  footer,
}: MessageListProps<T>) {
  return (
    <div className={containerClassName}>
      {header}

      {groups.map((group) => (
        <div key={group.key}>
          {renderDivider?.(group.key)}
          <div className={groupClassName}>
            {group.items.map((item, idx) => renderItem(item, idx))}
          </div>
        </div>
      ))}

      {footer}
    </div>
  );
}
