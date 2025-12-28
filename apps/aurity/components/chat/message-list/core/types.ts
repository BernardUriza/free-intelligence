/**
 * Message List Core Types
 *
 * Shared interfaces for all message-list components
 */

import type { FIMessage } from '@aurity-standalone/types/assistant';

/** Message role */
export type MessageRole = 'user' | 'assistant';

/** Base message props */
export interface BaseMessageProps {
  /** Is this a user message */
  isUser: boolean;
}

/** Message with content */
export interface MessageWithContent extends BaseMessageProps {
  /** Message content */
  content: string;
  /** Timestamp */
  timestamp: string;
}

/** Full message props (from FIMessage) */
export interface FullMessageProps {
  /** The message object */
  message: FIMessage;
  /** Is streaming (for cursor) */
  isStreaming?: boolean;
}

/** Messages grouped by date */
export interface MessageGroup {
  /** Date key (yyyy-MM-dd) */
  date: string;
  /** Messages in this date */
  messages: FIMessage[];
}

/** Action button state */
export interface ActionState {
  /** Is copied */
  copied: boolean;
  /** Is speaking TTS */
  speaking: boolean;
}
