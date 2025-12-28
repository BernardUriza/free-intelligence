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
        <span className="
          absolute -top-1 -right-1
          w-5 h-5 rounded-full
          bg-red-500 text-white
          text-xs font-bold
          flex items-center justify-center
        ">
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
        <div className={`
          absolute bottom-2 right-2
          text-xs font-mono
          transition-colors
          ${isOverLimit ? 'fi-text-error' : isNearLimit ? 'text-yellow-400' : 'text-slate-500'}
        `}>
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
    <div className="flex items-center gap-2 text-slate-400 text-sm py-2">
      <Loader2 className="w-4 h-4 animate-spin" />
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
      <AlertCircle className="w-5 h-5 fi-text-error flex-shrink-0 mt-0.5" />

      <div className="flex-1">
        <p className="text-red-300 font-medium mb-1">Error al enviar mensaje</p>
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
          className="flex items-start gap-3 animate-pulse"
        >
          <div className="fi-message-skeleton">
            {/* Header */}
            <div className="flex items-center gap-2 mb-3">
              <div className="h-3 w-32 bg-slate-700/50 rounded" />
              <div className="h-3 w-4 bg-slate-700/50 rounded" />
            </div>

            {/* Content lines */}
            <div className="fi-stack-sm">
              <div className="h-3 w-full bg-slate-700/30 rounded" />
              <div className="h-3 w-5/6 bg-slate-700/30 rounded" />
              <div className="h-3 w-4/6 bg-slate-700/30 rounded" />
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

      <h3 className="text-lg font-medium fi-text mb-2">
        {title}
      </h3>

      {description && (
        <p className="text-sm text-slate-500 mb-6 max-w-sm">
          {description}
        </p>
      )}

      {action && (
        <Button
          onClick={action.onClick}
          variant="primary"
          className="bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700"
        >
          {action.label}
        </Button>
      )}
    </div>
  );
}
