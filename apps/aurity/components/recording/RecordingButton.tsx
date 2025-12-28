/**
 * RecordingButton - Shared Recording Button Component
 *
 * A configurable circular button for recording controls.
 * Used by: RecordingControls (medical), VoiceMicButton (chat)
 *
 * Features:
 * - Multiple sizes (sm, md, lg, xl)
 * - Configurable colors per state
 * - Icon customization
 * - Accessibility (aria-label, disabled states)
 * - Optional pulse animations
 */

'use client';

import { forwardRef } from 'react';
import { Loader2 } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { BUTTON_SIZES, type ButtonSize } from './types';

export interface RecordingButtonProps {
  /** Button size variant */
  size?: ButtonSize;
  /** Background color (Tailwind classes) */
  bgColor: string;
  /** Icon to display */
  icon: LucideIcon;
  /** Whether icon should spin (for loading states) */
  iconSpin?: boolean;
  /** Icon color (Tailwind classes, default: text-white) */
  iconColor?: string;
  /** Whether button is disabled */
  disabled?: boolean;
  /** Click handler */
  onClick: () => void;
  /** Accessibility label */
  ariaLabel: string;
  /** Additional button classes */
  className?: string;
  /** Border/ring styles for accessibility */
  borderStyle?: string;
  /** Animation classes (e.g., animate-heartbeat) */
  animate?: string;
}

export const RecordingButton = forwardRef<HTMLButtonElement, RecordingButtonProps>(
  function RecordingButton(
    {
      size = 'md',
      bgColor,
      icon: Icon,
      iconSpin = false,
      iconColor = 'text-white',
      disabled = false,
      onClick,
      ariaLabel,
      className = '',
      borderStyle = '',
      animate = '',
    },
    ref
  ) {
    const sizeConfig = BUTTON_SIZES[size];
    const DisplayIcon = iconSpin ? Loader2 : Icon;

    return (
      <button
        ref={ref}
        onClick={onClick}
        disabled={disabled}
        aria-label={ariaLabel}
        className={`fi-recording-btn-base ${sizeConfig.button} ${bgColor} ${borderStyle} ${animate} ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'} ${className}`}
      >
        <DisplayIcon
          className={`${sizeConfig.icon} ${iconColor} ${iconSpin ? 'animate-spin' : ''}`}
        />
      </button>
    );
  }
);
