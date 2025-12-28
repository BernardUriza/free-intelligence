/**
 * FIChatInput Component
 *
 * Card: FI-ONBOARD-002
 * Chat input for conversing with Free-Intelligence
 */

import { useState, useRef, useEffect, type KeyboardEvent } from 'react';
import { Button } from '@/components/ui/button';

export interface FIChatInputProps {
  /** Callback when message is sent */
  onSend: (message: string) => void;

  /** Input disabled state */
  disabled?: boolean;

  /** Placeholder text */
  placeholder?: string;

  /** Auto-focus on mount */
  autoFocus?: boolean;

  /** Maximum message length */
  maxLength?: number;

  /** Show character count */
  showCharCount?: boolean;

  /** Additional CSS classes */
  className?: string;
}

/**
 * Chat input component for Free-Intelligence conversations
 *
 * Features:
 * - Enter to send, Shift+Enter for newline
 * - Validation (min 1 char, max configurable)
 * - Character counter
 * - Auto-resize textarea
 * - Accessible ARIA labels
 * - Neo-minimalist glassmorphism design
 *
 * @example
 * ```tsx
 * <FIChatInput
 *   onSend={(msg) => console.log('Sent:', msg)}
 *   placeholder="Pregúntale a Free-Intelligence..."
 *   autoFocus
 *   showCharCount
 * />
 * ```
 */
export function FIChatInput({
  onSend,
  disabled = false,
  placeholder = 'Escribe tu mensaje...',
  autoFocus = false,
  maxLength = 2000,
  showCharCount = false,
  className = '',
}: FIChatInputProps) {
  const [message, setMessage] = useState('');
  const [rows, setRows] = useState(1);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-focus on mount
  useEffect(() => {
    if (autoFocus && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, [autoFocus]);

  // Auto-resize textarea based on content
  useEffect(() => {
    if (textareaRef.current) {
      // Reset height to auto to get correct scrollHeight
      textareaRef.current.style.height = 'auto';

      const scrollHeight = textareaRef.current.scrollHeight;
      const lineHeight = 24; // Approximate line height in pixels
      const newRows = Math.min(Math.max(1, Math.ceil(scrollHeight / lineHeight)), 6);

      setRows(newRows);
      textareaRef.current.style.height = `${scrollHeight}px`;
    }
  }, [message]);

  /**
   * Handle Enter key (send) vs Shift+Enter (newline)
   */
  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  /**
   * Send message (with validation)
   */
  const handleSend = () => {
    const trimmed = message.trim();

    // Validation
    if (!trimmed) {
      return; // Empty message
    }

    if (trimmed.length > maxLength) {
      return; // Too long
    }

    // Send message
    onSend(trimmed);

    // Clear input
    setMessage('');
    setRows(1);

    // Refocus
    if (textareaRef.current) {
      textareaRef.current.focus();
    }
  };

  const charCount = message.length;
  const isOverLimit = charCount > maxLength;
  const isNearLimit = charCount > maxLength * 0.9;

  return (
    <div className={`relative ${className}`}>
      <div
        className={`${isOverLimit ? 'fi-chat-input-container-error' : 'fi-chat-input-container'} ${disabled ? 'opacity-50 cursor-not-allowed' : 'hover:border-slate-600/60'}`}
      >
        {/* Textarea */}
        <textarea
          ref={textareaRef}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          placeholder={placeholder}
          rows={rows}
          maxLength={maxLength + 100} // Allow typing slightly over to show error
          className="fi-chat-textarea"
          aria-label="Message input"
          aria-describedby={showCharCount ? 'char-count' : undefined}
        />

        {/* Send Button */}
        <Button
          onClick={handleSend}
          disabled={disabled || !message.trim() || isOverLimit}
          className={message.trim() && !isOverLimit ? 'fi-chat-send-btn-active' : 'fi-chat-send-btn'}
          aria-label="Send message"
          variant="ghost"
          size="sm"
        >
          Enviar
        </Button>
      </div>

      {/* Character Count & Help Text */}
      <div className="flex items-center justify-between mt-2 px-1">
        <div className="fi-text-xs/60">
          <kbd className="px-1.5 py-0.5 bg-slate-800/60 rounded fi-text font-mono text-[10px]">
            Enter
          </kbd>{' '}
          para enviar •{' '}
          <kbd className="px-1.5 py-0.5 bg-slate-800/60 rounded fi-text font-mono text-[10px]">
            Shift + Enter
          </kbd>{' '}
          para nueva línea
        </div>

        {showCharCount && (
          <span
            id="char-count"
            className={`fi-text-xs-medium ${isOverLimit ? 'fi-text-error' : isNearLimit ? 'text-yellow-400' : 'text-slate-400/60'}`}
            aria-live="polite"
          >
            {charCount} / {maxLength}
          </span>
        )}
      </div>
    </div>
  );
}
