'use client';

/**
 * ChatWidgetInput Component
 *
 * Input area with auto-resize textarea and send button
 */

import { Send, Loader2 } from 'lucide-react';
import { AutoResizeTextarea } from './ChatUtilities';
import { Button } from '@/components/ui/button';

export interface ChatWidgetInputProps {
  /** Current message value */
  message: string;

  /** Is sending message */
  loading: boolean;

  /** Placeholder text */
  placeholder?: string;

  /** Footer text */
  footer?: string;

  /** Callbacks */
  onMessageChange: (value: string) => void;
  onSend: () => void;
}

export function ChatWidgetInput({
  message,
  loading,
  placeholder = 'Escribe tu mensaje...',
  footer,
  onMessageChange,
  onSend,
}: ChatWidgetInputProps) {
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      onSend();
    }
  };

  const canSend = message.trim().length > 0 && !loading;

  return (
    <>
      <div className="flex gap-2 items-end">
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

        <Button
          onClick={onSend}
          disabled={!canSend}
          className={canSend ? 'chat-send-btn-active' : 'chat-send-btn-disabled'}
          aria-label="Enviar mensaje"
          variant="primary"
          size="sm"
          type="button"
        >
          {loading ? <Loader2 className="h-5 w-5 animate-spin" /> : <Send className="h-5 w-5" />}
        </Button>
      </div>
      {footer && <p className="chat-footer-text">{footer}</p>}
    </>
  );
}
