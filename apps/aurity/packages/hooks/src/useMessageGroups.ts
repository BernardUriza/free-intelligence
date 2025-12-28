/**
 * useMessageGroups Hook
 *
 * Groups consecutive messages from the same sender and adds date dividers.
 * Inspired by Discord, WhatsApp, and iMessage grouping patterns.
 *
 * Features:
 * - Group consecutive messages from same sender within time threshold
 * - Add "Today", "Yesterday", or date dividers between days
 * - Calculate message position (first/middle/last) for styling
 *
 * References:
 * - https://github.com/sejr/react-messenger
 * - https://virtuoso.dev/virtuoso-message-list/examples/grouped-messages/
 * - https://getstream.io/chat/docs/sdk/react-native/ui-components/message-simple/
 */

import { useMemo } from 'react';
import type { FIMessage } from '@aurity-standalone/types/assistant';

// ============================================================================
// TYPES
// ============================================================================

export type MessagePosition = 'single' | 'first' | 'middle' | 'last';
export type DateDividerType = 'today' | 'yesterday' | 'date';

export interface ProcessedMessage extends FIMessage {
  /** Generated ID (uses message.id or generates from index + timestamp) */
  id: string;
  /** Position in message group (for border radius styling) */
  position: MessagePosition;
  /** Is this the first message of its group? */
  startsSequence: boolean;
  /** Is this the last message of its group? */
  endsSequence: boolean;
  /** Should show avatar (only for last in sequence) */
  showAvatar: boolean;
  /** Should show timestamp (only for last in sequence) */
  showTimestamp: boolean;
  /** Should show sender name (only for first in sequence) */
  showSenderName: boolean;
}

export interface DateDivider {
  type: 'divider';
  dividerType: DateDividerType;
  date: Date;
  label: string;
}

export type GroupedItem = ProcessedMessage | DateDivider;

export interface UseMessageGroupsOptions {
  /** Messages to process */
  messages: FIMessage[];
  /** Time threshold to group messages (ms). Default: 60000 (1 min) */
  groupThresholdMs?: number;
  /** Locale for date formatting */
  locale?: string;
}

export interface UseMessageGroupsReturn {
  /** Processed items (messages + dividers) */
  items: GroupedItem[];
  /** Just the processed messages (no dividers) */
  processedMessages: ProcessedMessage[];
  /** Date dividers */
  dividers: DateDivider[];
}

// ============================================================================
// DATE HELPERS
// ============================================================================

/**
 * Check if two dates are the same day
 */
function isSameDay(date1: Date, date2: Date): boolean {
  return (
    date1.getFullYear() === date2.getFullYear() &&
    date1.getMonth() === date2.getMonth() &&
    date1.getDate() === date2.getDate()
  );
}

/**
 * Check if date is today
 */
function isToday(date: Date): boolean {
  return isSameDay(date, new Date());
}

/**
 * Check if date is yesterday
 */
function isYesterday(date: Date): boolean {
  const yesterday = new Date();
  yesterday.setDate(yesterday.getDate() - 1);
  return isSameDay(date, yesterday);
}

/**
 * Get date divider label
 */
function getDateLabel(date: Date, locale: string = 'es-MX'): string {
  if (isToday(date)) {
    return 'Hoy';
  }
  if (isYesterday(date)) {
    return 'Ayer';
  }
  // Format: "Lunes, 15 de enero"
  return date.toLocaleDateString(locale, {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
  });
}

/**
 * Get date divider type
 */
function getDateDividerType(date: Date): DateDividerType {
  if (isToday(date)) return 'today';
  if (isYesterday(date)) return 'yesterday';
  return 'date';
}

// ============================================================================
// HOOK IMPLEMENTATION
// ============================================================================

export function useMessageGroups({
  messages,
  groupThresholdMs = 60000, // 1 minute
  locale = 'es-MX',
}: UseMessageGroupsOptions): UseMessageGroupsReturn {
  return useMemo(() => {
    if (messages.length === 0) {
      return { items: [], processedMessages: [], dividers: [] };
    }

    const items: GroupedItem[] = [];
    const processedMessages: ProcessedMessage[] = [];
    const dividers: DateDivider[] = [];

    let lastDate: Date | null = null;
    let _lastSender: string | null = null;
    let lastTimestamp: number | null = null;

    messages.forEach((message, index) => {
      const messageDate = new Date(message.timestamp);
      const messageTimestamp = messageDate.getTime();
      const nextMessage = messages[index + 1];
      const prevMessage = messages[index - 1];

      // ================================================================
      // DATE DIVIDER CHECK
      // ================================================================
      const needsDateDivider = !lastDate || !isSameDay(lastDate, messageDate);

      if (needsDateDivider) {
        const divider: DateDivider = {
          type: 'divider',
          dividerType: getDateDividerType(messageDate),
          date: messageDate,
          label: getDateLabel(messageDate, locale),
        };
        items.push(divider);
        dividers.push(divider);
        lastDate = messageDate;
      }

      // ================================================================
      // MESSAGE GROUPING LOGIC
      // ================================================================
      const sameSenderAsPrev =
        prevMessage &&
        prevMessage.role === message.role &&
        isSameDay(new Date(prevMessage.timestamp), messageDate);

      const withinTimeThresholdOfPrev =
        lastTimestamp !== null &&
        messageTimestamp - lastTimestamp < groupThresholdMs;

      const sameSenderAsNext =
        nextMessage &&
        nextMessage.role === message.role &&
        isSameDay(new Date(nextMessage.timestamp), messageDate);

      const nextTimestamp = nextMessage
        ? new Date(nextMessage.timestamp).getTime()
        : null;

      const withinTimeThresholdOfNext =
        nextTimestamp !== null &&
        nextTimestamp - messageTimestamp < groupThresholdMs;

      // Determine if this message continues from previous
      const continuesFromPrev = sameSenderAsPrev && withinTimeThresholdOfPrev;

      // Determine if next message continues from this one
      const continuesIntoNext = sameSenderAsNext && withinTimeThresholdOfNext;

      // ================================================================
      // CALCULATE POSITION
      // ================================================================
      let position: MessagePosition;
      if (!continuesFromPrev && !continuesIntoNext) {
        position = 'single';
      } else if (!continuesFromPrev && continuesIntoNext) {
        position = 'first';
      } else if (continuesFromPrev && continuesIntoNext) {
        position = 'middle';
      } else {
        position = 'last';
      }

      // ================================================================
      // BUILD PROCESSED MESSAGE
      // ================================================================
      // Generate stable ID if not present
      const messageId = message.id || `msg-${index}-${messageTimestamp}`;

      const processedMessage: ProcessedMessage = {
        ...message,
        id: messageId,
        position,
        startsSequence: !continuesFromPrev,
        endsSequence: !continuesIntoNext,
        showAvatar: !continuesIntoNext, // Show avatar on last message of sequence
        showTimestamp: !continuesIntoNext, // Show timestamp on last message
        showSenderName: !continuesFromPrev && message.role === 'assistant', // Show name on first assistant message
      };

      items.push(processedMessage);
      processedMessages.push(processedMessage);

      // Update tracking
      _lastSender = message.role;
      lastTimestamp = messageTimestamp;
    });

    return { items, processedMessages, dividers };
  }, [messages, groupThresholdMs, locale]);
}

// ============================================================================
// UTILITY: Check if item is a divider
// ============================================================================
export function isDateDivider(item: GroupedItem): item is DateDivider {
  return 'type' in item && item.type === 'divider';
}

// ============================================================================
// UTILITY: Get border radius classes based on position
// ============================================================================
export function getMessageBorderRadius(
  position: MessagePosition,
  isUser: boolean
): string {
  const baseRadius = 'rounded-2xl';

  switch (position) {
    case 'single':
      return isUser
        ? `${baseRadius} rounded-br-sm`
        : `${baseRadius} rounded-bl-sm`;

    case 'first':
      return isUser
        ? `${baseRadius} rounded-br-md`
        : `${baseRadius} rounded-bl-md`;

    case 'middle':
      return isUser
        ? 'rounded-l-2xl rounded-r-md'
        : 'rounded-r-2xl rounded-l-md';

    case 'last':
      return isUser
        ? `${baseRadius} rounded-tr-md rounded-br-sm`
        : `${baseRadius} rounded-tl-md rounded-bl-sm`;

    default:
      return baseRadius;
  }
}
