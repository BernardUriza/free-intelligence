'use client';

/**
 * ScrollToBottomFAB - Single Responsibility: Scroll navigation FAB
 *
 * SOLID Principles:
 * - S: Only handles scroll-to-bottom button with unread badge
 * - O: Extensible via className and badge customization
 * - I: Minimal focused interface
 */

import { memo } from 'react';
import { ArrowDown } from 'lucide-react';
import { Button } from '@/components/ui/button';

export interface ScrollToBottomFABProps {
  onClick: (e: React.MouseEvent) => void;
  unreadCount?: number;
  visible: boolean;
  className?: string;
}

export const ScrollToBottomFAB = memo(function ScrollToBottomFAB({
  onClick,
  unreadCount = 0,
  visible,
  className = '',
}: ScrollToBottomFABProps) {
  if (!visible) return null;

  const hasUnread = unreadCount > 0;
  const ariaLabel = hasUnread ? `${unreadCount} mensajes nuevos` : 'Ir al final';
  const title = hasUnread ? `${unreadCount} nuevos` : 'Ir al final';

  return (
    <Button
      onClick={onClick}
      className={`chat-scroll-fab ${className}`}
      aria-label={ariaLabel}
      title={title}
      variant="ghost"
      size="sm"
      type="button"
    >
      <ArrowDown className="w-4 h-4" />
      {hasUnread && (
        <span className="chat-scroll-fab-badge" aria-hidden="true">
          {unreadCount > 9 ? '9+' : unreadCount}
        </span>
      )}
    </Button>
  );
});
