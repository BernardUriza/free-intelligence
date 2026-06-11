'use client';

/**
 * fi-glass · Composer — chat text input (auto-resize + Enter-to-send).
 * Extracted from aurity ChatWidgetInput on 2026-06-01 (Americio).
 *
 * Fully callback-driven and voice-agnostic: the mic/send live OUTSIDE the
 * composer (in the app's toolbar), so "composer without voice" is the default
 * state — render this alone and there is no voice anywhere.
 *
 * CONFIGURABILITY (fire test): the app controls value/submit via props and
 * dresses every element via className props — no fi-glass edit needed to restyle
 * or to drop voice (there is none to drop here).
 */

import { type CSSProperties, type KeyboardEvent } from 'react';
import { AutoResizeTextarea } from './AutoResizeTextarea';

export interface ComposerProps {
  /** Current message value */
  message: string;
  /** Is sending message (disables input) */
  loading?: boolean;
  /** Placeholder text */
  placeholder?: string;
  /** Called on every edit */
  onMessageChange: (value: string) => void;
  /** Called on Enter (without Shift) */
  onSend: () => void;
  /** Max rows before the textarea scrolls */
  maxRows?: number;
  /** Class for the outer area wrapper */
  areaClassName?: string;
  /** Class for the AutoResizeTextarea wrapper */
  wrapperClassName?: string;
  /** Inline style for the input wrapper (e.g. flex-grow so it fills the area). */
  wrapperStyle?: CSSProperties;
  /** Class for the <textarea> itself */
  textareaClassName?: string;
}

export function Composer({
  message,
  loading = false,
  placeholder = 'Escribe tu mensaje...',
  onMessageChange,
  onSend,
  maxRows = 5,
  areaClassName,
  wrapperClassName,
  wrapperStyle,
  textareaClassName,
}: ComposerProps) {
  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      onSend();
    }
  };

  return (
    <div className={areaClassName}>
      <AutoResizeTextarea
        value={message}
        onChange={(e) => onMessageChange(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        disabled={loading}
        maxRows={maxRows}
        showCounter={false}
        wrapperClassName={wrapperClassName}
        wrapperStyle={wrapperStyle}
        className={textareaClassName}
      />
    </div>
  );
}
