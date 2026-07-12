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

import {
  type ClipboardEventHandler,
  type CSSProperties,
  type KeyboardEvent,
  type Ref,
} from 'react';
import { AutoResizeTextarea } from './AutoResizeTextarea';

export interface ComposerProps {
  /** Current message value */
  message: string;
  /**
   * A turn is streaming. Blocks SUBMIT (Enter is a no-op) so a second turn
   * can't fire, but NEVER blocks editing — the user keeps typing the next
   * message while the assistant responds (ChatGPT parity, B3-FIGLASS-COMPOSER-FOCUS-1).
   */
  loading?: boolean;
  /**
   * Genuinely disable EDITING (auth blocked, readonly, quota/capacity, terminal
   * error) — this is the only state that sets the <textarea> disabled and lets
   * the browser drop focus. Streaming is `loading`, not `disabled`.
   */
  disabled?: boolean;
  /** Placeholder text */
  placeholder?: string;
  /** Called on every edit */
  onMessageChange: (value: string) => void;
  /** Called on Enter (without Shift) */
  onSend: () => void;
  /**
   * Paste hook on the textarea (OG118-IMAGE-UPLOAD-1): the surface intercepts
   * pasted image files here (calling `preventDefault` itself); plain-text paste
   * is untouched. Omit for the previous behavior.
   */
  onPaste?: ClipboardEventHandler<HTMLTextAreaElement>;
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
  /**
   * Optional stable id for the inner <textarea> (B3-FIGLASS-A11Y-1). Omit it and
   * the textarea self-generates an accessible default — pass one only when the
   * app needs a predictable handle (label `for=`, autofill, tests).
   */
  id?: string;
  /** Optional stable name for the inner <textarea> (B3-FIGLASS-A11Y-1). */
  name?: string;
  /**
   * Typed ref to the inner <textarea> (B3-FIGLASS-10) so the owner can manage
   * focus (e.g. refocus after dictation/send/stream) without touching DOM
   * internals.
   */
  textareaRef?: Ref<HTMLTextAreaElement>;
}

export function Composer({
  message,
  loading = false,
  disabled = false,
  placeholder = 'Escribe tu mensaje...',
  onMessageChange,
  onSend,
  onPaste,
  maxRows = 5,
  areaClassName,
  wrapperClassName,
  wrapperStyle,
  textareaClassName,
  id,
  name,
  textareaRef,
}: ComposerProps) {
  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      // Gate the SUBMIT, not the editing: a streaming turn (loading) or a truly
      // disabled composer must not fire a second turn. The empty-message guard
      // stays in the consumer (pinned by the existing contract test).
      if (loading || disabled) return;
      onSend();
    }
  };

  return (
    <div className={areaClassName}>
      <AutoResizeTextarea
        ref={textareaRef}
        id={id}
        name={name}
        value={message}
        onChange={(e) => onMessageChange(e.target.value)}
        onKeyDown={handleKeyDown}
        onPaste={onPaste}
        placeholder={placeholder}
        disabled={disabled}
        maxRows={maxRows}
        showCounter={false}
        wrapperClassName={wrapperClassName}
        wrapperStyle={wrapperStyle}
        className={textareaClassName}
      />
    </div>
  );
}
