'use client';

/**
 * Chat Utility Components
 *
 * Practical, mundane but essential UX improvements:
 * - Scroll to bottom button
 * - Auto-resize textarea
 * - Character counter
 * - Loading states
 * - Error states with retry
 */

import { useState, useEffect, useRef, type TextareaHTMLAttributes } from 'react';
import { ArrowDown, AlertCircle, RefreshCw, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';

// ============================================================================
// SCROLL TO BOTTOM BUTTON
// ============================================================================

export interface ScrollToBottomButtonProps {
  /** Container element to scroll */
  containerId: string;

  /** Show button when scrolled up by this many pixels */
  threshold?: number;

  /** Additional CSS classes */
  className?: string;
}

export function ScrollToBottomButton({
  containerId,
  threshold = 100,
  className = '',
}: ScrollToBottomButtonProps) {
  const [isVisible, setIsVisible] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);

  useEffect(() => {
    const container = document.getElementById(containerId);
    if (!container) return;

    const handleScroll = () => {
      const { scrollTop, scrollHeight, clientHeight } = container;
      const distanceFromBottom = scrollHeight - scrollTop - clientHeight;

      // Show button if scrolled up beyond threshold
      setIsVisible(distanceFromBottom > threshold);
    };

    container.addEventListener('scroll', handleScroll);
    handleScroll(); // Initial check

    return () => container.removeEventListener('scroll', handleScroll);
  }, [containerId, threshold]);

  const scrollToBottom = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();

    const container = document.getElementById(containerId);
    if (!container) return;

    container.scrollTo({
      top: container.scrollHeight,
      behavior: 'smooth',
    });

    setUnreadCount(0);
  };

  if (!isVisible) return null;

  return (
    <Button
      onClick={scrollToBottom}
      className={`fi-fab-scroll ${className}`}
      aria-label="Scroll to bottom"
      title="Ir al final"
      variant="ghost"
      size="sm"
      type="button"
    >
      <ArrowDown className="w-4 h-4" />

      {/* Unread count badge */}
      {unreadCount > 0 && (
        <span className="chat-unread-badge">
          {unreadCount}
        </span>
      )}
    </Button>
  );
}

// ============================================================================
// AUTO-RESIZE TEXTAREA
// ============================================================================

export interface AutoResizeTextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
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

// ============================================================================
// MESSAGE LOADING STATE
// ============================================================================

export function MessageLoadingState({ text = 'Enviando...' }: { text?: string }) {
  return (
    <div className="chat-loading-inline">
      <Loader2 className="chat-spinner-sm" />
      <span>{text}</span>
    </div>
  );
}

// ============================================================================
// MESSAGE ERROR STATE
// ============================================================================

export interface MessageErrorStateProps {
  error: string;
  onRetry?: () => void;
  onDismiss?: () => void;
}

export function MessageErrorState({ error, onRetry, onDismiss }: MessageErrorStateProps) {
  return (
    <div className="fi-alert-error">
      <AlertCircle className="chat-error-icon" />

      <div className="flex-1">
        <p className="chat-error-title">Error al enviar mensaje</p>
        <p className="fi-text-error/80 text-xs">{error}</p>
      </div>

      <div className="flex gap-2">
        {onRetry && (
          <Button onClick={onRetry} className="fi-btn-danger-sm" variant="danger" size="sm" type="button">
            <RefreshCw className="w-3.5 h-3.5" />
            Reintentar
          </Button>
        )}

        {onDismiss && (
          <Button onClick={onDismiss} className="fi-btn-ghost-danger" variant="ghost" size="sm" type="button">
            Cerrar
          </Button>
        )}
      </div>
    </div>
  );
}

// ============================================================================
// SKELETON LOADING (for messages)
// ============================================================================

export function MessageSkeleton({ count = 1 }: { count?: number }) {
  return (
    <>
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className="chat-skeleton-row"
        >
          <div className="fi-message-skeleton">
            {/* Header */}
            <div className="chat-skeleton-header">
              <div className="chat-skeleton-bar-wide" />
              <div className="chat-skeleton-bar-narrow" />
            </div>

            {/* Content lines */}
            <div className="fi-stack-sm">
              <div className="chat-skeleton-line-full" />
              <div className="chat-skeleton-line-5of6" />
              <div className="chat-skeleton-line-4of6" />
            </div>
          </div>
        </div>
      ))}
    </>
  );
}

// ============================================================================
// EMPTY STATE
// ============================================================================

export interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: {
    label: string;
    onClick: () => void;
  };
}

export function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="fi-empty-state">
      {icon && (
        <div className="mb-4 text-slate-600">
          {icon}
        </div>
      )}

      <h3 className="chat-empty-title-lg">
        {title}
      </h3>

      {description && (
        <p className="chat-empty-desc">
          {description}
        </p>
      )}

      {action && (
        <Button
          onClick={action.onClick}
          variant="primary"
          className="chat-empty-cta-gradient"
        >
          {action.label}
        </Button>
      )}
    </div>
  );
}
