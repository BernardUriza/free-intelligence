'use client';

/**
 * fi-glass · AutoResizeTextarea — textarea that grows with content up to maxRows.
 * Extracted verbatim from aurity ChatUtilities on 2026-06-01 (Americio).
 *
 * Pure: React hooks + DOM measurement only. All styling arrives via className /
 * wrapperClassName, so an app dresses it however it likes.
 */

import {
  useEffect,
  useRef,
  useState,
  type TextareaHTMLAttributes,
} from 'react';

export interface AutoResizeTextareaProps
  extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  /** Max rows before scrolling */
  maxRows?: number;
  /** Show character counter */
  showCounter?: boolean;
  /** Max characters */
  maxLength?: number;
  /** Additional wrapper CSS classes */
  wrapperClassName?: string;
}

export function AutoResizeTextarea({
  value,
  onChange,
  maxRows = 5,
  showCounter = false,
  maxLength,
  wrapperClassName = '',
  className = '',
  ...props
}: AutoResizeTextareaProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const [rows, setRows] = useState(1);

  // Auto-resize on content change
  useEffect(() => {
    if (!textareaRef.current) return;

    const textarea = textareaRef.current;
    textarea.style.height = 'auto';

    const lineHeight = 20; // Approximate line height
    const newRows = Math.min(
      Math.ceil(textarea.scrollHeight / lineHeight),
      maxRows
    );

    setRows(newRows);
    textarea.style.height = `${newRows * lineHeight}px`;
  }, [value, maxRows]);

  const charCount = typeof value === 'string' ? value.length : 0;
  const isNearLimit = maxLength && charCount > maxLength * 0.9;
  const isOverLimit = maxLength && charCount > maxLength;

  return (
    <div className={`relative ${wrapperClassName}`}>
      <textarea
        ref={textareaRef}
        value={value}
        onChange={onChange}
        maxLength={maxLength}
        className={`
          resize-none
          ${className}
        `}
        rows={rows}
        {...props}
      />

      {/* Character counter */}
      {showCounter && maxLength && (
        <div className={isOverLimit ? 'chat-char-counter-error' : isNearLimit ? 'chat-char-counter-warning' : 'chat-char-counter-ok'}>
          {charCount}/{maxLength}
        </div>
      )}
    </div>
  );
}
