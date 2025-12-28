'use client';

/**
 * UnreadDivider - Shows "X nuevos mensajes" divider
 *
 * SOLID: Single responsibility - only renders unread divider
 */

import { memo, useState, useCallback, useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import { ChevronDown } from 'lucide-react';
import { Button } from '@/components/ui/button';
import type { FIMessage } from '@aurity-standalone/types/assistant';

export interface UnreadDividerProps {
  count: number;
  onScrollToBottom?: () => void;
  animate?: boolean;
}

export const UnreadDivider = memo(function UnreadDivider({
  count,
  onScrollToBottom,
  animate = true,
}: UnreadDividerProps) {
  if (count <= 0) return null;

  const content = (
    <div className="chat-unread-divider">
      <div className="chat-unread-line" />
      <Button
        onClick={onScrollToBottom}
        className="chat-unread-pill"
        aria-label={`${count} mensajes nuevos. Click para ir al más reciente.`}
        variant="ghost"
        size="sm"
        type="button"
      >
        <span>{count === 1 ? '1 mensaje nuevo' : `${count} mensajes nuevos`}</span>
        {onScrollToBottom && <ChevronDown className="w-3.5 h-3.5" aria-hidden="true" />}
      </Button>
      <div className="chat-unread-line-right" />
    </div>
  );

  if (!animate) return content;

  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -10 }}
      transition={{ duration: 0.3 }}
    >
      {content}
    </motion.div>
  );
});

// ============================================================================
// HOOK: Track unread messages
// ============================================================================

export interface UseUnreadMessagesOptions {
  messages: FIMessage[];
  lastReadMessageId?: string | null;
  isVisible?: boolean;
}

export interface UseUnreadMessagesReturn {
  unreadCount: number;
  firstUnreadId: string | null;
  markAllAsRead: () => void;
  isUnread: (messageId: string) => boolean;
}

export function useUnreadMessages({
  messages,
  lastReadMessageId = null,
  isVisible = true,
}: UseUnreadMessagesOptions): UseUnreadMessagesReturn {
  const [lastReadId, setLastReadId] = useState<string | null>(lastReadMessageId);
  const messagesRef = useRef(messages);
  messagesRef.current = messages;

  const getUnreadInfo = useCallback(() => {
    if (!lastReadId || messages.length === 0) {
      return { unreadCount: 0, firstUnreadId: null };
    }

    const lastReadIndex = messages.findIndex(
      (m) => m.id === lastReadId || m.metadata?.id === lastReadId
    );

    if (lastReadIndex === -1 || lastReadIndex === messages.length - 1) {
      return { unreadCount: 0, firstUnreadId: null };
    }

    const unreadMessages = messages.slice(lastReadIndex + 1);
    const unreadAssistantMessages = unreadMessages.filter((m) => m.role === 'assistant');

    return {
      unreadCount: unreadAssistantMessages.length,
      firstUnreadId:
        unreadAssistantMessages.length > 0
          ? unreadAssistantMessages[0].id || unreadAssistantMessages[0].metadata?.id || null
          : null,
    };
  }, [messages, lastReadId]);

  const { unreadCount, firstUnreadId } = getUnreadInfo();

  const markAllAsRead = useCallback(() => {
    if (messages.length > 0) {
      const lastMessage = messages[messages.length - 1];
      setLastReadId(lastMessage.id || lastMessage.metadata?.id || null);
    }
  }, [messages]);

  useEffect(() => {
    if (isVisible && unreadCount > 0) {
      const timer = setTimeout(markAllAsRead, 2000);
      return () => clearTimeout(timer);
    }
  }, [isVisible, unreadCount, markAllAsRead]);

  const isUnread = useCallback(
    (messageId: string) => {
      if (!lastReadId) return false;

      const lastReadIndex = messages.findIndex(
        (m) => m.id === lastReadId || m.metadata?.id === lastReadId
      );
      const messageIndex = messages.findIndex(
        (m) => m.id === messageId || m.metadata?.id === messageId
      );

      return messageIndex > lastReadIndex;
    },
    [messages, lastReadId]
  );

  return { unreadCount, firstUnreadId, markAllAsRead, isUnread };
}
