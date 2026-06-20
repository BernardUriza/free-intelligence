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
  useId,
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
    id,
    name,
    ...props
  },
  ref,
) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  useImperativeHandle(ref, () => textareaRef.current as HTMLTextAreaElement);
  const [rows, setRows] = useState(1);

  // B3-FIGLASS-A11Y-1: a textarea with no id/name makes the browser warn "a
  // form field element should have an id or name" (seen in og118 staging). Give
  // it a stable generated default when the consumer provides nothing, while
  // letting any consumer override either one. name falls back to the resolved
  // id so autofill/labels have a consistent handle.
  const generatedId = useId();
  const resolvedId = id ?? `fi-glass-composer-${generatedId}`;
  const resolvedName = name ?? resolvedId;

  // Auto-resize on content change
  useEffect(() => {
    if (!textareaRef.current) return;

    const textarea = textareaRef.current;
    // B3-FIGLASS-16: reset to the MINIMAL state before measuring. The rows
    // attribute left over from the previous render sets the textarea's
    // intrinsic height, and scrollHeight can never report less than that — so
    // a textarea that had grown to 5 rows kept measuring 5 rows forever, even
    // after its content was deleted (grew on type, never shrank on delete).
    // One row + auto height makes scrollHeight track the content alone.
    textarea.rows = 1;
    textarea.style.height = 'auto';

    // B3-FIGLASS-15: measure the REAL line height instead of assuming 20px.
    // The old hardcode made an empty textarea compute ceil(24/20) = 2 rows with
    // the default 16px/24px font — a permanently inflated empty composer. The
    // floor of 1 row also guards jsdom (scrollHeight 0) and any glitched
    // measurement from ever collapsing the input to 0.
    const computed = window.getComputedStyle(textarea);
    const parsed = parseFloat(computed.lineHeight);
    const lineHeight = Number.isFinite(parsed) && parsed > 0 ? parsed : 20;
    const newRows = Math.max(
      1,
      Math.min(Math.ceil(textarea.scrollHeight / lineHeight), maxRows),
    );

    setRows(newRows);
    // Restore rows imperatively too: when newRows equals the previous render's
    // value React skips the attribute, which would leave the reset `1` behind.
    textarea.rows = newRows;
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
        id={resolvedId}
        name={resolvedName}
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
