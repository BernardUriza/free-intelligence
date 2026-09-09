'use client';

/**
 * fi-glass · ComposerActionSlot — one control on the composer's rail
 * (B3-FIGLASS-SHELL-PRIMITIVES-1D).
 *
 * A consumer says WHAT the control is (icon, label, handler) and what it looks
 * like (`className`); the slot says how a composer control behaves — the box,
 * the touch minimum on a narrow container, the label that yields to the icon,
 * and the rail-keep contract for a control that must survive the collapse.
 */

import type { ButtonHTMLAttributes, ReactNode } from 'react';
import { withTouchTarget } from '../shell/touchTarget';
import {
  FI_COMPOSER_ACTION_LABEL_CLASS,
  useComposerActionStyle,
  withComposerAction,
  type ComposerActionVariant,
} from './composerActionStyle';

export interface ComposerActionSlotProps
  extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'children'> {
  /** `primary` is the send-shaped square; `secondary` the outlined pill chip. */
  variant?: ComposerActionVariant;
  icon: ReactNode;
  /** Text beside the icon. Hidden on a compact composer unless the flag says otherwise. */
  label?: ReactNode;
  hideLabelWhenCompact?: boolean;
  /**
   * Keep this control reachable when the compact rail collapses — the contract
   * for something live the user must be able to stop (a call in progress).
   */
  keepWhenRailCollapses?: boolean;
  labelClassName?: string;
}

export function ComposerActionSlot({
  variant = 'secondary',
  icon,
  label,
  hideLabelWhenCompact = true,
  keepWhenRailCollapses = false,
  className,
  labelClassName,
  type = 'button',
  ...rest
}: ComposerActionSlotProps) {
  useComposerActionStyle();
  return (
    <button
      type={type}
      className={withTouchTarget(withComposerAction(variant, className))}
      {...(keepWhenRailCollapses ? { 'data-fi-rail-keep': '' } : {})}
      {...rest}
    >
      {icon}
      {label != null && label !== false && (
        <span
          className={
            labelClassName
              ? `${FI_COMPOSER_ACTION_LABEL_CLASS} ${labelClassName}`
              : FI_COMPOSER_ACTION_LABEL_CLASS
          }
          {...(hideLabelWhenCompact ? { 'data-fi-compact-hide': '' } : {})}
        >
          {label}
        </span>
      )}
    </button>
  );
}
