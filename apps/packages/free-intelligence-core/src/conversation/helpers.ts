/**
 * Conversation helpers — pure, deterministic primitives for building and
 * summarizing ConversationRecords. No React, no browser, no transport.
 *
 * Privacy by structure: `sanitizeConversationMessage` builds a NEW message with
 * exactly the allowed subset (role / content / timestamp). Any other field a
 * ChatMessage may carry now or later — `id`, `thinking`, `metadata`, a future
 * tool payload or token — is dropped by construction, not by an allow/deny list
 * someone must remember to update. The initial privacy guarantee is the
 * restriction, not PII heuristics.
 *
 * Determinism: helpers that stamp a time accept an optional `now` so tests are
 * reproducible; they fall back to the wall clock only when it is omitted.
 */

import type { ChatMessage } from '../chat/message';
import type { ConversationRecord, ConversationSummary } from './record';

/** Schema version stamped on every record created here. */
export const CONVERSATION_SCHEMA_VERSION = 1;

/** Fallback title when there is no usable user message yet. */
const DEFAULT_TITLE = 'New chat';
const TITLE_MAX = 60;
const PREVIEW_MAX = 120;

/** Collapse whitespace and truncate to `max` chars with an ellipsis. Pure. */
function truncate(text: string, max: number): string {
  const t = text.trim().replace(/\s+/g, ' ');
  if (t.length <= max) return t;
  return `${t.slice(0, Math.max(0, max - 1)).trimEnd()}…`;
}

/**
 * Reduce a ChatMessage to the only fields safe to persist: role, content, and
 * timestamp. Drops id, thinking, metadata, and anything else by construction.
 */
export function sanitizeConversationMessage(message: ChatMessage): ChatMessage {
  return {
    role: message.role,
    content: message.content,
    timestamp: message.timestamp,
  };
}

/** Title from the first non-empty user message; `DEFAULT_TITLE` otherwise. */
export function deriveConversationTitle(
  messages: ChatMessage[],
  max: number = TITLE_MAX,
): string {
  const firstUser = messages.find(
    (m) => m.role === 'user' && m.content.trim() !== '',
  );
  if (!firstUser) return DEFAULT_TITLE;
  return truncate(firstUser.content, max) || DEFAULT_TITLE;
}

/** Preview from the last non-empty message of any role; `''` otherwise. */
export function deriveConversationPreview(
  messages: ChatMessage[],
  max: number = PREVIEW_MAX,
): string {
  for (let i = messages.length - 1; i >= 0; i--) {
    if (messages[i].content.trim() !== '') {
      return truncate(messages[i].content, max);
    }
  }
  return '';
}

/** Arguments for {@link createConversationRecord}. */
export interface CreateConversationRecordArgs {
  /** Stable id (doubles as the backend session_id). */
  id: string;
  /** Initial thread; sanitized before storing. Default: empty. */
  messages?: ChatMessage[];
  /** ISO timestamp to stamp createdAt/updatedAt. Default: now. */
  now?: string;
}

/** Build a fresh, sanitized record with derived title + preview. */
export function createConversationRecord(
  args: CreateConversationRecordArgs,
): ConversationRecord {
  const now = args.now ?? new Date().toISOString();
  const messages = (args.messages ?? []).map(sanitizeConversationMessage);
  return {
    id: args.id,
    title: deriveConversationTitle(messages),
    createdAt: now,
    updatedAt: now,
    messages,
    preview: deriveConversationPreview(messages),
    schemaVersion: CONVERSATION_SCHEMA_VERSION,
  };
}

/** Project a record to its light summary — excludes `messages`. */
export function summarizeConversation(
  record: ConversationRecord,
): ConversationSummary {
  return {
    id: record.id,
    title: record.title,
    createdAt: record.createdAt,
    updatedAt: record.updatedAt,
    preview: record.preview,
  };
}
