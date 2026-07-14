/**
 * ConversationRecord — the persisted shape of one local-first conversation.
 *
 * DD-002B1: og118 (and every future fi-glass shell) needs the transcript to
 * survive a refresh and a list of past chats for a sidebar. The record is the
 * unit a ConversationLibrary stores; the summary is the light row a sidebar
 * lists without paying for the full message array. Pure data — no React, no
 * browser, no transport. The `id` doubles as the backend session_id so the
 * local transcript and the server's conversation store key the same thread.
 */

import type { ChatMessage } from '../chat/message';

export interface ConversationRecord {
  /** Stable id. Doubles as the backend session_id for the same thread. */
  id: string;
  /** Human-readable title. Derived from the first user message unless the user
   * renamed it, in which case `titleCustom` is set and the title is preserved
   * across future message persists. */
  title: string;
  /** True when the user explicitly renamed this conversation. A custom title is
   * never re-derived from messages on persist. Absent/false ⇒ auto-derived. */
  titleCustom?: boolean;
  /** ISO 8601 creation timestamp. */
  createdAt: string;
  /** ISO 8601 timestamp of the last change. */
  updatedAt: string;
  /** The thread, sanitized for storage (role/content/timestamp only). */
  messages: ChatMessage[];
  /** Snippet of the last non-empty message, for the sidebar. */
  preview: string;
  /** ISO 8601 timestamp of when the user pinned this conversation. Absent ⇒ not
   * pinned. A timestamp (not a boolean) so the pinned section orders by
   * last-pinned first without a separate counter. */
  pinnedAt?: string;
  /** ISO 8601 timestamp of when the user archived this conversation. Absent ⇒
   * active. Archiving is the reversible alternative to delete: the record keeps
   * its messages and moves to the archived section. */
  archivedAt?: string;
  /** Schema version of this record, for forward migrations. */
  schemaVersion: number;
}

/** A light row for listing conversations in a sidebar (no messages). */
export interface ConversationSummary {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  preview: string;
  pinnedAt?: string;
  archivedAt?: string;
}
