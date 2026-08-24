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
 * The metadata delta of an organization mutation (rename / pin / archive).
 *
 * These three mutations used to exist only as whole-record transforms, which
 * forced every transport to ship the whole record — and a whole-record write
 * from a device holding a stale copy silently drops the flags it never meant to
 * touch (CONV-CONCURRENCY-1). The delta expresses the same semantics as the
 * SMALLEST thing that changed, so a transport can send just that.
 *
 * `null` means CLEAR the field; an omitted key means LEAVE IT ALONE. That is
 * precisely the distinction a full-record put cannot express — an absent field
 * and a deliberately-cleared one look identical on the wire.
 */
export interface ConversationMetadataPatch {
  title?: string;
  titleCustom?: boolean;
  /** ISO timestamp to pin at, or `null` to unpin. */
  pinnedAt?: string | null;
  /** ISO timestamp to archive at, or `null` to unarchive. */
  archivedAt?: string | null;
  /** Only a rename stamps this: pinning/archiving must not fake recency. */
  updatedAt?: string;
}

/**
 * Apply a metadata delta to a record. `null` clears the field, an omitted key
 * leaves it untouched. Pure — the single place the merge rule is written, so the
 * local (apply-then-put) and remote (send-the-delta) paths cannot drift.
 */
export function applyConversationMetadataPatch(
  record: ConversationRecord,
  patch: ConversationMetadataPatch,
): ConversationRecord {
  const next: ConversationRecord = { ...record };
  if (patch.title !== undefined) next.title = patch.title;
  if (patch.titleCustom !== undefined) next.titleCustom = patch.titleCustom;
  if (patch.updatedAt !== undefined) next.updatedAt = patch.updatedAt;
  if (patch.pinnedAt !== undefined) {
    if (patch.pinnedAt === null) delete next.pinnedAt;
    else next.pinnedAt = patch.pinnedAt;
  }
  if (patch.archivedAt !== undefined) {
    if (patch.archivedAt === null) delete next.archivedAt;
    else next.archivedAt = patch.archivedAt;
  }
  return next;
}

/**
 * The delta of a user rename. A non-empty title is stored verbatim (trimmed,
 * whitespace-collapsed, capped at TITLE_MAX) and marks the record `titleCustom`
 * so future persists never re-derive it. An empty/whitespace title reverts to
 * the derived title and clears the custom flag (emptyTitlePolicy:
 * revert-to-derived). Needs the record because reverting has to re-derive from
 * its messages.
 */
export function conversationRenamePatch(
  record: ConversationRecord,
  rawTitle: string,
  now?: string,
): ConversationMetadataPatch {
  const trimmed = rawTitle.trim().replace(/\s+/g, ' ');
  const ts = now ?? new Date().toISOString();
  if (trimmed === '') {
    return {
      title: deriveConversationTitle(record.messages),
      titleCustom: false,
      updatedAt: ts,
    };
  }
  return { title: trimmed.slice(0, TITLE_MAX), titleCustom: true, updatedAt: ts };
}

/**
 * The delta of a pin/unpin. Pinning lifts the record out of the archive — a pin
 * is an explicit "keep this in front of me", incompatible with archived.
 * `updatedAt` is deliberately absent: pinning is organization, not content, and
 * must not fake recency in the active list.
 */
export function conversationPinPatch(
  pinned: boolean,
  now?: string,
): ConversationMetadataPatch {
  if (pinned) {
    return { pinnedAt: now ?? new Date().toISOString(), archivedAt: null };
  }
  return { pinnedAt: null };
}

/**
 * The delta of an archive/unarchive. Archiving clears any pin (an archived
 * conversation cannot stay in the pinned section). Unarchiving rejoins the
 * active list at the record's own `updatedAt`, which — like pinning — is not
 * touched.
 */
export function conversationArchivePatch(
  archived: boolean,
  now?: string,
): ConversationMetadataPatch {
  if (archived) {
    return { archivedAt: now ?? new Date().toISOString(), pinnedAt: null };
  }
  return { archivedAt: null };
}

/**
 * Apply a user rename to a record. Thin composition of the delta and the merge
 * rule above — kept so callers holding a whole record (the local, single-writer
 * path) do not each re-implement it.
 */
export function renameConversationRecord(
  record: ConversationRecord,
  rawTitle: string,
  now?: string,
): ConversationRecord {
  return applyConversationMetadataPatch(
    record,
    conversationRenamePatch(record, rawTitle, now),
  );
}

/** Pin or unpin a record (whole-record form of `conversationPinPatch`). */
export function setConversationPinned(
  record: ConversationRecord,
  pinned: boolean,
  now?: string,
): ConversationRecord {
  return applyConversationMetadataPatch(record, conversationPinPatch(pinned, now));
}

/** Archive or unarchive a record (whole-record form of `conversationArchivePatch`). */
export function setConversationArchived(
  record: ConversationRecord,
  archived: boolean,
  now?: string,
): ConversationRecord {
  return applyConversationMetadataPatch(
    record,
    conversationArchivePatch(archived, now),
  );
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
    ...(record.projectId ? { projectId: record.projectId } : {}),
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
