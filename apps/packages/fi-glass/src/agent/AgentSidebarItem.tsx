'use client';

/**
 * fi-glass · sidebar/resource item primitives (B3-FIGLASS-SHELL-PRIMITIVES-1A).
 *
 * The shell anatomy that og118 hand-wrote twice (`og-chat-item` for conversations,
 * `og-project-item` for projects — structural twins per the audit) lifted into the
 * framework so og118/slate/paper render a selectable resource row with actions
 * without re-authoring the skeleton. The framework owns the *anatomy* (row,
 * selected/hover/keyboard, title/subtitle/meta slots, inline-rename state machine,
 * destructive action revealed on hover/touch); the consumer owns the *meaning*
 * (what the resource is, the copy, the handlers, the confirm).
 *
 * - {@link AgentSidebarItem} — the row (slots + selected/keyboard/hover).
 * - {@link EditableResourceItem} — a row whose title edits in place (the #283
 *   rename affordance, now framework-owned, with the same Enter/Escape/blur
 *   contract — Escape's blur must not re-commit the discarded draft).
 * - {@link ItemActionSlot} / {@link DestructiveActionSlot} — hover/touch-revealed
 *   action buttons; the destructive variant tints danger and the consumer wires
 *   its own confirm.
 * - {@link useInlineRename} — the rename state machine on its own, for any surface
 *   that needs in-place editing without the full row.
 */

import {
  type ChangeEvent,
  type KeyboardEvent,
  type MouseEvent as ReactMouseEvent,
  type ReactNode,
  useCallback,
  useRef,
  useState,
} from 'react';
import { withTouchTarget } from '../shell/touchTarget';
import {
  FI_SIDEBAR_ITEM_CLASS,
  FI_ITEM_BODY_CLASS,
  FI_ITEM_TITLE_CLASS,
  FI_ITEM_SUBTITLE_CLASS,
  FI_ITEM_META_CLASS,
  FI_ITEM_ACTION_CLASS,
  FI_ITEM_ACTION_DANGER_CLASS,
  FI_RESOURCE_RENAME_INPUT_CLASS,
  useSidebarItemStyle,
} from './sidebarItemStyle';

function joinClasses(...parts: (string | false | null | undefined)[]): string {
  return parts.filter(Boolean).join(' ');
}

// ---------------------------------------------------------------------------
// Action slots
// ---------------------------------------------------------------------------

export interface ItemActionSlotProps {
  /** Accessible label — the consumer supplies the copy (e.g. "Renombrar chat"). */
  label: string;
  /** Fired on click/activation; the click never bubbles to the row's onSelect. */
  onActivate: () => void;
  disabled?: boolean;
  /** Tint the action as destructive (danger color on hover). */
  danger?: boolean;
  className?: string;
  /** The glyph/icon to render inside the button. */
  children: ReactNode;
}

export function ItemActionSlot({
  label,
  onActivate,
  disabled = false,
  danger = false,
  className,
  children,
}: ItemActionSlotProps) {
  const cls = withTouchTarget(
    joinClasses(FI_ITEM_ACTION_CLASS, danger && FI_ITEM_ACTION_DANGER_CLASS, className),
  );
  return (
    <button
      type="button"
      className={cls}
      aria-label={label}
      disabled={disabled}
      onClick={(e) => {
        e.stopPropagation();
        if (!disabled) onActivate();
      }}
    >
      {children}
    </button>
  );
}

export type DestructiveActionSlotProps = Omit<ItemActionSlotProps, 'danger'>;

export function DestructiveActionSlot(props: DestructiveActionSlotProps) {
  return <ItemActionSlot {...props} danger />;
}

// ---------------------------------------------------------------------------
// Inline-rename state machine
// ---------------------------------------------------------------------------

export interface UseInlineRenameOptions {
  maxLength?: number;
  /**
   * What an empty draft means on commit. `revert` (default) calls `onRename('')`
   * so the consumer can fall back to an auto-derived title; `keep` cancels
   * silently and leaves the current value.
   */
  emptyPolicy?: 'revert' | 'keep';
}

export interface InlineRename {
  editing: boolean;
  draft: string;
  start: () => void;
  cancel: () => void;
  /** Spread onto the `<input>` — wires value, Enter/Escape/blur, and click-stop. */
  inputProps: {
    value: string;
    maxLength?: number;
    autoFocus: true;
    onChange: (e: ChangeEvent<HTMLInputElement>) => void;
    onBlur: () => void;
    onClick: (e: ReactMouseEvent) => void;
    onKeyDown: (e: KeyboardEvent) => void;
  };
}

export function useInlineRename(
  value: string,
  onRename: (next: string) => void,
  { maxLength, emptyPolicy = 'revert' }: UseInlineRenameOptions = {},
): InlineRename {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState('');
  // Escape sets this so the ensuing blur does not also commit the discarded draft.
  const cancelledRef = useRef(false);

  const start = useCallback(() => {
    cancelledRef.current = false;
    setDraft(value);
    setEditing(true);
  }, [value]);

  const cancel = useCallback(() => {
    cancelledRef.current = true;
    setEditing(false);
  }, []);

  const commit = useCallback(() => {
    if (cancelledRef.current) {
      cancelledRef.current = false;
      setEditing(false);
      return;
    }
    if (draft.trim() === '' && emptyPolicy === 'keep') {
      setEditing(false);
      return;
    }
    onRename(draft);
    setEditing(false);
  }, [draft, emptyPolicy, onRename]);

  return {
    editing,
    draft,
    start,
    cancel,
    inputProps: {
      value: draft,
      maxLength,
      autoFocus: true,
      onChange: (e) => setDraft(e.target.value),
      onBlur: commit,
      onClick: (e) => e.stopPropagation(),
      onKeyDown: (e) => {
        e.stopPropagation();
        if (e.key === 'Enter') {
          e.preventDefault();
          commit();
        } else if (e.key === 'Escape') {
          e.preventDefault();
          cancel();
        }
      },
    },
  };
}

// ---------------------------------------------------------------------------
// The row
// ---------------------------------------------------------------------------

export interface AgentSidebarItemProps {
  selected: boolean;
  onSelect: () => void;
  /** A plain string is wrapped in the title slot; a node (e.g. the rename input) is used as-is. */
  title: ReactNode;
  subtitle?: ReactNode;
  meta?: ReactNode;
  /** Action buttons rendered at the end of the row (e.g. {@link DestructiveActionSlot}). */
  actions?: ReactNode;
  disabled?: boolean;
  /** When the row is being edited in place: non-interactive, no hover-select. */
  editing?: boolean;
  /**
   * Fire `onSelect` even when the row is already selected, so the consumer can
   * treat the click as a toggle-off (an active-project row deselects). Default
   * false — a selected row is inert (re-clicking the open conversation is a no-op).
   */
  toggleable?: boolean;
  ariaLabel?: string;
  className?: string;
}

export function AgentSidebarItem({
  selected,
  onSelect,
  title,
  subtitle,
  meta,
  actions,
  disabled = false,
  editing = false,
  toggleable = false,
  ariaLabel,
  className,
}: AgentSidebarItemProps) {
  useSidebarItemStyle();
  const interactive = !disabled && !editing && (toggleable || !selected);
  const titleNode =
    typeof title === 'string' ? <span className={FI_ITEM_TITLE_CLASS}>{title}</span> : title;
  return (
    <div
      className={joinClasses(
        FI_SIDEBAR_ITEM_CLASS,
        selected && 'is-selected',
        editing && 'is-editing',
        className,
      )}
      role="button"
      tabIndex={0}
      aria-current={selected}
      aria-label={ariaLabel}
      onClick={() => interactive && onSelect()}
      onKeyDown={(e) => {
        if ((e.key === 'Enter' || e.key === ' ') && interactive) {
          e.preventDefault();
          onSelect();
        }
      }}
    >
      <div className={FI_ITEM_BODY_CLASS}>
        {titleNode}
        {subtitle != null && subtitle !== '' && (
          <span className={FI_ITEM_SUBTITLE_CLASS}>{subtitle}</span>
        )}
        {meta != null && meta !== '' && <span className={FI_ITEM_META_CLASS}>{meta}</span>}
      </div>
      {actions}
    </div>
  );
}

// ---------------------------------------------------------------------------
// The editable row (conversation list canary)
// ---------------------------------------------------------------------------

export interface EditableResourceItemProps {
  title: string;
  selected: boolean;
  onSelect: () => void;
  onRename: (next: string) => void;
  subtitle?: ReactNode;
  meta?: ReactNode;
  /** Extra actions (e.g. delete) rendered after the rename trigger. */
  actions?: ReactNode;
  disabled?: boolean;
  maxLength?: number;
  emptyPolicy?: 'revert' | 'keep';
  /** Accessible label for the rename trigger (consumer copy). */
  renameLabel: string;
  /** Accessible label for the rename input (consumer copy). */
  renameInputLabel: string;
  /** Glyph for the rename trigger; defaults to a pencil. */
  renameGlyph?: ReactNode;
  ariaLabel?: string;
}

export function EditableResourceItem({
  title,
  selected,
  onSelect,
  onRename,
  subtitle,
  meta,
  actions,
  disabled = false,
  maxLength,
  emptyPolicy,
  renameLabel,
  renameInputLabel,
  renameGlyph = '✎',
  ariaLabel,
}: EditableResourceItemProps) {
  const rename = useInlineRename(title, onRename, { maxLength, emptyPolicy });
  const titleNode = rename.editing ? (
    <input
      className={FI_RESOURCE_RENAME_INPUT_CLASS}
      aria-label={renameInputLabel}
      {...rename.inputProps}
    />
  ) : (
    title
  );
  return (
    <AgentSidebarItem
      selected={selected}
      onSelect={onSelect}
      disabled={disabled}
      editing={rename.editing}
      ariaLabel={ariaLabel}
      title={titleNode}
      subtitle={subtitle}
      meta={meta}
      actions={
        !rename.editing && (
          <>
            <ItemActionSlot
              label={renameLabel}
              disabled={disabled}
              onActivate={rename.start}
            >
              {renameGlyph}
            </ItemActionSlot>
            {actions}
          </>
        )
      }
    />
  );
}
