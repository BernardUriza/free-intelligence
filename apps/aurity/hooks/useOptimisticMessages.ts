/**
 * useOptimisticMessages Hook
 *
 * Implements optimistic UI pattern for chat messages:
 * - Shows message immediately with "sending" state
 * - Updates to "sent" when server confirms
 * - Shows "failed" state with retry option on error
 *
 * References:
 * - https://react.dev/reference/react/useOptimistic
 * - https://blog.logrocket.com/understanding-optimistic-ui-react-useoptimistic-hook/
 */

import { useOptimistic, useCallback, useTransition } from 'react';
import type { FIMessage } from '@aurity-standalone/types/assistant';

// ============================================================================
// TYPES
// ============================================================================

export type MessageStatus = 'sending' | 'sent' | 'failed';

export interface OptimisticMessage extends FIMessage {
  /** Message delivery status */
  status: MessageStatus;
  /** Temporary ID for optimistic messages */
  tempId?: string;
  /** Error message if failed */
  error?: string;
  /** Retry function if failed */
  retry?: () => void;
}

export interface UseOptimisticMessagesOptions {
  /** Current messages from server/storage */
  messages: FIMessage[];
  /** Function to send message to server */
  sendToServer: (content: string) => Promise<FIMessage>;
}

export interface UseOptimisticMessagesReturn {
  /** Messages including optimistic ones */
  optimisticMessages: OptimisticMessage[];
  /** Send a message with optimistic update */
  sendMessage: (content: string) => Promise<void>;
  /** Is a message being sent? */
  isPending: boolean;
  /** Retry a failed message */
  retryMessage: (tempId: string) => Promise<void>;
  /** Dismiss a failed message */
  dismissFailedMessage: (tempId: string) => void;
}

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

/** Generate temporary ID for optimistic messages */
const generateTempId = () => `temp_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;

/** Convert server messages to optimistic format */
const toOptimisticMessages = (messages: FIMessage[]): OptimisticMessage[] =>
  messages.map((msg) => ({ ...msg, status: 'sent' as const }));

// ============================================================================
// HOOK IMPLEMENTATION
// ============================================================================

export function useOptimisticMessages({
  messages,
  sendToServer,
}: UseOptimisticMessagesOptions): UseOptimisticMessagesReturn {
  const [isPending, startTransition] = useTransition();

  // Store failed messages for retry
  const failedMessagesRef = new Map<string, { content: string; retry: () => void }>();

  // Optimistic state reducer
  const [optimisticMessages, addOptimisticMessage] = useOptimistic<
    OptimisticMessage[],
    { type: 'add' | 'update' | 'remove'; message: Partial<OptimisticMessage> & { tempId?: string } }
  >(toOptimisticMessages(messages), (state, action) => {
    switch (action.type) {
      case 'add':
        // Add new optimistic message at the end
        return [
          ...state,
          {
            id: action.message.tempId || generateTempId(),
            role: 'user',
            content: action.message.content || '',
            timestamp: new Date().toISOString(),
            status: 'sending',
            tempId: action.message.tempId,
          } as OptimisticMessage,
        ];

      case 'update':
        // Update existing message (e.g., sending → sent or sending → failed)
        return state.map((msg) =>
          msg.tempId === action.message.tempId
            ? { ...msg, ...action.message }
            : msg
        );

      case 'remove':
        // Remove a message (e.g., dismiss failed)
        return state.filter((msg) => msg.tempId !== action.message.tempId);

      default:
        return state;
    }
  });

  // Send message with optimistic update
  const sendMessage = useCallback(
    async (content: string) => {
      const tempId = generateTempId();

      startTransition(async () => {
        // Immediately show optimistic message
        addOptimisticMessage({
          type: 'add',
          message: { content, tempId },
        });

        try {
          // Send to server
          const serverMessage = await sendToServer(content);

          // Update with server response (status: sent)
          addOptimisticMessage({
            type: 'update',
            message: {
              tempId,
              id: serverMessage.id,
              status: 'sent',
              timestamp: serverMessage.timestamp,
            },
          });
        } catch (error) {
          // Mark as failed
          const errorMessage = error instanceof Error ? error.message : 'Error al enviar';

          // Store for retry
          failedMessagesRef.set(tempId, {
            content,
            retry: () => sendMessage(content),
          });

          addOptimisticMessage({
            type: 'update',
            message: {
              tempId,
              status: 'failed',
              error: errorMessage,
            },
          });
        }
      });
    },
    [addOptimisticMessage, sendToServer, startTransition]
  );

  // Retry a failed message
  const retryMessage = useCallback(
    async (tempId: string) => {
      const failed = failedMessagesRef.get(tempId);
      if (!failed) return;

      // Remove failed message
      addOptimisticMessage({ type: 'remove', message: { tempId } });
      failedMessagesRef.delete(tempId);

      // Resend
      await sendMessage(failed.content);
    },
    [addOptimisticMessage, sendMessage]
  );

  // Dismiss a failed message without retrying
  const dismissFailedMessage = useCallback(
    (tempId: string) => {
      addOptimisticMessage({ type: 'remove', message: { tempId } });
      failedMessagesRef.delete(tempId);
    },
    [addOptimisticMessage]
  );

  return {
    optimisticMessages,
    sendMessage,
    isPending,
    retryMessage,
    dismissFailedMessage,
  };
}
