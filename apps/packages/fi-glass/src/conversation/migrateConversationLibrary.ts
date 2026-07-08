/**
 * migrateConversationLibrary — one-time local→cloud transcript migration.
 *
 * When a shell flips from a local library (IndexedDB) to a remote one (the
 * account signed in and the cloud store is now authoritative), the transcripts
 * that already live in the browser must not be stranded. This copies every
 * source record the target does not already have — target wins on id collision
 * (the cloud copy may be newer, written from another device), and the source is
 * left intact (never destructive: the local data remains a fallback until the
 * user clears it). Idempotent: a second run finds nothing to copy.
 */

import type { ConversationLibrary } from '@free-intelligence/core';

export interface MigrateConversationsResult {
  /** How many records were copied into the target. */
  migrated: number;
  /** How many source records were skipped because the target already had them. */
  skipped: number;
}

export async function migrateConversationLibrary(
  source: ConversationLibrary,
  target: ConversationLibrary,
): Promise<MigrateConversationsResult> {
  const [sourceList, targetList] = await Promise.all([source.list(), target.list()]);
  const existing = new Set(targetList.map((summary) => summary.id));
  let migrated = 0;
  let skipped = 0;
  for (const summary of sourceList) {
    if (existing.has(summary.id)) {
      skipped += 1;
      continue;
    }
    const record = await source.get(summary.id);
    if (!record) continue;
    await target.put(record);
    migrated += 1;
  }
  return { migrated, skipped };
}
