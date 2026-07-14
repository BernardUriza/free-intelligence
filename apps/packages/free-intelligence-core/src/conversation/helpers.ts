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
 * Reduce a ChatMessage to the fields safe to persist: role, author, content,
 * timestamp, plus the glass-box `trace` when present (B3-FIGLASS-TRACE-
 * PERSISTENCE-1).
 *
 * Privacy by structure: `metadata` is DROPPED on purpose — apps stuff secrets
 * there (a `Bearer` token, tool payloads), so it must never reach durable
 * storage. `trace` and `author` are the deliberate exceptions, not holes in that
 * boundary: both carry only non-sensitive, already-user-visible provenance —
 * plan-step labels/summaries (model-authored, rendered live), tool NAMES (core's
 * ToolCall is {id,name,server,isError} — no arguments/payloads), source URLs,
 * and the public name of the persona that spoke. Persisting what the live turn
 * already showed leaks nothing new — and dropping the author would re-anonymize
 * every bubble on reload, which is the bug the contract exists to prevent.
 * Included only when present, so a plain message stays minimal; id, thinking and
 * metadata are still dropped by construction.
 */
export function sanitizeConversationMessage(message: ChatMessage): ChatMessage {
  return {
    role: message.role,
    content: message.content,
    timestamp: message.timestamp,
    ...(message.author ? { author: message.author } : {}),
    ...(message.trace ? { trace: message.trace } : {}),
    // Attached images are user-visible message CONTENT (OG118-IMAGE-UPLOAD-1),
    // not metadata — dropping them would blank the picture on reload the way
    // dropping `author` used to anonymize bubbles. Producers downscale before
    // encoding, so the persisted base64 stays within the record size caps.
    ...(message.images && message.images.length > 0
      ? { images: message.images.map((i) => ({ mediaType: i.mediaType, data: i.data })) }
      : {}),
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

/**
 * Resolve the title to stamp when persisting messages: a user-set (custom)
 * title is preserved; otherwise it is derived from the messages. This is the
 * SSOT that keeps `persist` from clobbering a rename on the next message.
 */
export function resolveConversationTitle(
  messages: ChatMessage[],
  prev?: { title: string; titleCustom?: boolean },
): string {
  if (prev?.titleCustom && prev.title.trim() !== '') return prev.title;
  return deriveConversationTitle(messages);
}

/**
 * Apply a user rename to a record. A non-empty title is stored verbatim
 * (trimmed, whitespace-collapsed, capped at TITLE_MAX) and marks the record
 * `titleCustom` so future persists never re-derive it. An empty/whitespace
 * title reverts to the derived title and clears the custom flag
 * (emptyTitlePolicy: revert-to-derived). Pure — stamps `updatedAt` from `now`.
 */
export function renameConversationRecord(
  record: ConversationRecord,
  rawTitle: string,
  now?: string,
): ConversationRecord {
  const trimmed = rawTitle.trim().replace(/\s+/g, ' ');
  const ts = now ?? new Date().toISOString();
  if (trimmed === '') {
    return {
      ...record,
      title: deriveConversationTitle(record.messages),
      titleCustom: false,
      updatedAt: ts,
    };
  }
  return {
    ...record,
    title: trimmed.slice(0, TITLE_MAX),
    titleCustom: true,
    updatedAt: ts,
  };
}

/**
 * Pin or unpin a record. Pinning stamps `pinnedAt` (the pinned section orders by
 * last-pinned first) and lifts the record out of the archive — a pin is an
 * explicit "keep this in front of me", incompatible with archived. Unpinning
 * drops the field entirely. `updatedAt` is deliberately NOT touched: pinning is
 * organization, not content, and must not fake recency in the active list.
 */
export function setConversationPinned(
  record: ConversationRecord,
  pinned: boolean,
  now?: string,
): ConversationRecord {
  if (pinned) {
    const { archivedAt: _archivedAt, ...rest } = record;
    return { ...rest, pinnedAt: now ?? new Date().toISOString() };
  }
  const { pinnedAt: _pinnedAt, ...rest } = record;
  return rest;
}

/**
 * Archive or unarchive a record. Archiving stamps `archivedAt` and clears any
 * pin (an archived conversation cannot stay in the pinned section). Unarchiving
 * drops the field and the record rejoins the active list at its own
 * `updatedAt` — which, like pinning, is deliberately not touched.
 */
export function setConversationArchived(
  record: ConversationRecord,
  archived: boolean,
  now?: string,
): ConversationRecord {
  if (archived) {
    const { pinnedAt: _pinnedAt, ...rest } = record;
    return { ...rest, archivedAt: now ?? new Date().toISOString() };
  }
  const { archivedAt: _archivedAt, ...rest } = record;
  return rest;
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
    ...(record.pinnedAt ? { pinnedAt: record.pinnedAt } : {}),
    ...(record.archivedAt ? { archivedAt: record.archivedAt } : {}),
  };
}

/** Lowercase + strip diacritics, so "métodos" matches "metodos" (es-MX). */
function normalizeForSearch(text: string): string {
  return text
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '');
}

/**
 * Filter summaries by a free-text query over title + preview (CONV-SEARCH-1).
 * Case- and diacritic-insensitive; every whitespace-separated term must match
 * somewhere (AND semantics). An empty/whitespace query returns the input
 * untouched. Pure — feed the result to {@link organizeConversationSummaries}.
 */
export function filterConversationSummaries(
  summaries: ConversationSummary[],
  query: string,
): ConversationSummary[] {
  const terms = normalizeForSearch(query).split(/\s+/).filter(Boolean);
  if (terms.length === 0) return summaries;
  return summaries.filter((s) => {
    const haystack = normalizeForSearch(`${s.title} ${s.preview}`);
    return terms.every((t) => haystack.includes(t));
  });
}

/** The sidebar's three sections, each already in display order. */
export interface OrganizedConversations {
  /** Pinned, last-pinned first. */
  pinned: ConversationSummary[];
  /** Neither pinned nor archived, most recently updated first. */
  active: ConversationSummary[];
  /** Archived, most recently archived first. */
  archived: ConversationSummary[];
}

/**
 * Split summaries into the pinned / active / archived sections every sidebar
 * renders. Pure and total: a summary lands in exactly one section (`archivedAt`
 * wins over a stray `pinnedAt`, though the pin/archive transformers never
 * produce that state). ISO 8601 timestamps sort lexicographically.
 */
export function organizeConversationSummaries(
  summaries: ConversationSummary[],
): OrganizedConversations {
  const pinned: ConversationSummary[] = [];
  const active: ConversationSummary[] = [];
  const archived: ConversationSummary[] = [];
  for (const s of summaries) {
    if (s.archivedAt) archived.push(s);
    else if (s.pinnedAt) pinned.push(s);
    else active.push(s);
  }
  pinned.sort((a, b) => (b.pinnedAt ?? '').localeCompare(a.pinnedAt ?? ''));
  active.sort((a, b) => b.updatedAt.localeCompare(a.updatedAt));
  archived.sort((a, b) => (b.archivedAt ?? '').localeCompare(a.archivedAt ?? ''));
  return { pinned, active, archived };
}
