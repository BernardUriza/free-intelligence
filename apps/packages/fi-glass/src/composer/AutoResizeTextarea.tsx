'use client';

/**
 * fi-glass · AutoResizeTextarea — textarea that grows with content up to maxRows.
 * Extracted verbatim from aurity ChatUtilities on 2026-06-01 (Americio).
 *
 * Pure: React hooks + DOM measurement only. All styling arrives via className /
 * wrapperClassName, so an app dresses it however it likes.
 */

import {
  forwardRef,
  useEffect,
  useImperativeHandle,
  useRef,
  useState,
  type CSSProperties,
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
  /**
   * Inline style for the wrapper div. Lets the Composer/surface own the input's
   * layout (e.g. `flex: 1 1 0%` so it fills a flex composer) WITHOUT a consumer
   * reaching into the internal `.relative` wrapper from CSS.
   */
  wrapperStyle?: CSSProperties;
}

/**
 * Forwards its ref to the inner <textarea> (B3-FIGLASS-10) so an owner (e.g. the
 * conversation surface) can manage focus through a TYPED handle instead of
 * reaching into this component's internal DOM.
 */
export const AutoResizeTextarea = forwardRef<
  HTMLTextAreaElement,
  AutoResizeTextareaProps
>(function AutoResizeTextarea(
  {
    value,
    onChange,
    maxRows = 5,
    showCounter = false,
    maxLength,
    wrapperClassName = '',
    wrapperStyle,
    className = '',
    ...props
  },
  ref,
) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  useImperativeHandle(ref, () => textareaRef.current as HTMLTextAreaElement);
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
    // Fill the wrapper width. Set imperatively (not via the style prop) so it
    // never collides with the imperative height above on re-render — a composer
    // textarea should always span its container.
    textarea.style.width = '100%';
  }, [value, maxRows]);

  const charCount = typeof value === 'string' ? value.length : 0;
  const isNearLimit = maxLength && charCount > maxLength * 0.9;
  const isOverLimit = maxLength && charCount > maxLength;

  return (
    <div className={`relative ${wrapperClassName}`} style={wrapperStyle}>
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
});
