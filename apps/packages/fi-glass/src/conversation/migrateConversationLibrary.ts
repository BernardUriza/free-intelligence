/**
 * migrateConversationLibrary — local→cloud transcript migration.
 *
 * When a shell flips from a local library (IndexedDB) to a remote one (the
 * account signed in and the cloud store is now authoritative), the transcripts
 * that already live in the browser must not be stranded. A record the target
 * lacks is copied. A record BOTH have is merged when the source was written
 * after the target: the shell writes locally while the cloud store is still
 * connecting, so skipping the collision lost exactly those turns. The merge is
 * a union of messages (target metadata wins); nothing is ever removed, and the
 * source is left intact. Idempotent: a second run finds nothing to write.
 */

import {
  type ChatMessage,
  type ConversationLibrary,
  type ConversationRecord,
  deriveConversationPreview,
  resolveConversationTitle,
} from '@free-intelligence/core';

export interface MigrateConversationsResult {
  /** How many records were copied into the target. */
  migrated: number;
  /** How many existing target records gained messages only the source had. */
  merged: number;
  /** How many source records needed no write (the target already had everything). */
  skipped: number;
}

/** Persisted messages carry no id (sanitize drops it); this is what a reload shows. */
function messageKey(message: ChatMessage): string {
  return `${message.role}\u0000${message.timestamp ?? ''}\u0000${message.content}`;
}

/**
 * Union of two copies of the same conversation: every message of `target`,
 * plus the ones only `source` has, ordered by timestamp (stable for ties).
 * `target` keeps its title, flags and project.
 *
 * @returns `target` itself (same reference) when `source` adds nothing.
 */
export function mergeConversationRecords(
  target: ConversationRecord,
  source: ConversationRecord,
): ConversationRecord {
  const known = new Set(target.messages.map(messageKey));
  const missing = source.messages.filter((m) => !known.has(messageKey(m)));
  if (missing.length === 0) return target;
  const messages = [...target.messages, ...missing]
    .map((message, order) => ({ message, order }))
    .sort((a, b) => (a.message.timestamp ?? '').localeCompare(b.message.timestamp ?? '') || a.order - b.order)
    .map(({ message }) => message);
  return {
    ...target,
    messages,
    title: resolveConversationTitle(messages, target),
    preview: deriveConversationPreview(messages),
    updatedAt: source.updatedAt > target.updatedAt ? source.updatedAt : target.updatedAt,
  };
}

export async function migrateConversationLibrary(
  source: ConversationLibrary,
  target: ConversationLibrary,
): Promise<MigrateConversationsResult> {
  const [sourceList, targetList] = await Promise.all([source.list(), target.list()]);
  const existing = new Map(targetList.map((summary) => [summary.id, summary]));
  let migrated = 0;
  let merged = 0;
  let skipped = 0;
  for (const summary of sourceList) {
    const theirs = existing.get(summary.id);
    if (theirs && summary.updatedAt <= theirs.updatedAt) {
      skipped += 1;
      continue;
    }
    const record = await source.get(summary.id);
    if (!record) continue;
    if (!theirs) {
      await target.put(record);
      migrated += 1;
      continue;
    }
    const current = await target.get(summary.id);
    const next = current ? mergeConversationRecords(current, record) : record;
    if (next === current) {
      skipped += 1;
      continue;
    }
    await target.put(next);
    merged += 1;
  }
  return { migrated, merged, skipped };
}
