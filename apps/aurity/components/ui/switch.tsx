/**
 * Switch Component - Stub
 *
 * Minimal implementation to unblock build.
 * TODO: Implement full switch functionality
 */

import React from 'react';

export interface SwitchProps {
  id?: string;
  checked?: boolean;
  onCheckedChange?: (checked: boolean) => void;
  disabled?: boolean;
  className?: string;
}

export function Switch({ id, checked = false, onCheckedChange, disabled = false, className = '' }: SwitchProps) {
  return (
    <button
      id={id}
      type="button"
      role="switch"
      aria-checked={checked}
      disabled={disabled}
      onClick={() => onCheckedChange?.(!checked)}
      className={`inline-flex h-6 w-11 items-center rounded-full transition-colors ${
        checked ? 'bg-emerald-500' : 'bg-slate-700'
      } ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'} ${className}`}
    >
      <span
        className={`inline-block h-4 w-4 rounded-full bg-white transition-transform ${
          checked ? 'translate-x-6' : 'translate-x-1'
        }`}
      />
    </button>
  );
}
