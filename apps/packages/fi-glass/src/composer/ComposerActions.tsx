'use client';

/**
 * fi-glass · ComposerActions — the composer's "+" : one trigger for everything
 * the user can ADD to a turn.
 *
 * It does not implement a menu. It renders aurity's menu (`ActionMenu`) — the
 * framework's SSOT, portaled and opening upward — with a `+` trigger instead of
 * aurity's `⋮`. og118 grew an `ImagePlus` button the day it gained vision, blind
 * to the fact that the shell already had this exact affordance; the fix is not a
 * second menu, it is consuming the first one.
 *
 * Attaching an image is contributed by the framework as an ACTION; the app
 * appends its own (upload a document to the active project, …). A new capability
 * lands in the menu instead of crowding the rail with another icon.
 */

import { Plus } from 'lucide-react';
import { ActionMenu, type MenuAction } from '../menu/ActionMenu';

export type ComposerAction = MenuAction;

export interface ComposerActionsProps {
  actions: ComposerAction[];
  /** Disable the trigger (a turn is streaming, the composer is disabled). */
  disabled?: boolean;
  /** aria-label/title of the trigger. Default: "Añadir". */
  label?: string;
  className?: string;
  iconClassName?: string;
  menuClassName?: string;
  itemClassName?: string;
}

export function ComposerActions({
  actions,
  disabled = false,
  label = 'Añadir',
  className,
  iconClassName,
  menuClassName,
  itemClassName,
}: ComposerActionsProps) {
  return (
    <ActionMenu
      actions={actions}
      trigger={<Plus size={18} aria-hidden className={iconClassName} />}
      triggerLabel={label}
      triggerClassName={`fi-touch-target ${className ?? ''}`.trim()}
      triggerStyle={{
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'transparent',
        border: 'none',
        cursor: disabled ? 'default' : 'pointer',
        opacity: disabled ? 0.5 : 1,
        padding: '0.375rem',
        color: 'inherit',
      }}
      disabled={disabled}
      menuClassName={menuClassName}
      itemClassName={itemClassName}
      triggerAttribute="data-fi-composer-actions"
    />
  );
}
