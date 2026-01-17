'use client';

/**
 * ChatWidgetInput Component
 *
 * Clean input area with auto-resize textarea only.
 * Send button is now in ChatToolbar (ChatGPT style).
 */

import { AutoResizeTextarea } from './ChatUtilities';

export interface ChatWidgetInputProps {
  /** Current message value */
  message: string;

  /** Is sending message */
  loading: boolean;

  /** Placeholder text */
  placeholder?: string;

  /** Callbacks */
  onMessageChange: (value: string) => void;
  onSend: () => void;
}

export function ChatWidgetInput({
  message,
  loading,
  placeholder = 'Escribe tu mensaje...',
  onMessageChange,
  onSend,
}: ChatWidgetInputProps) {
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      onSend();
    }
  };

  return (
    <div className="chat-input-area-top">
      <AutoResizeTextarea
        value={message}
        onChange={(e) => onMessageChange(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        disabled={loading}
        maxRows={5}
        showCounter={false}
        wrapperClassName="flex-1"
        className="chat-textarea"
      />
    </div>
  );
}
