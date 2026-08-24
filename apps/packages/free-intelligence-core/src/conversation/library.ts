/**
 * ConversationLibrary — the storage contract for local-first conversations.
 *
 * A pure async interface: adapters implement it over IndexedDB (fi-glass), a
 * backend, or filesystem (later layers) without core taking a dependency on any
 * of them. `list` returns light summaries (cheap); `get` hydrates one full
 * record; `put` upserts; `delete`/`clear` remove. Keeping the contract in core
 * is what stops a reusable persistence primitive from being trapped in a
 * consumer app (DD-002-LESSON / framework-first-canary).
 */

import type { ConversationMetadataPatch } from './helpers';
import type { ConversationRecord, ConversationSummary } from './record';

export interface ConversationLibrary {
  /** All conversations as light summaries, newest `updatedAt` first. */
  list(): Promise<ConversationSummary[]>;
  /** The full record for `id`, or `null` if none. */
  get(id: string): Promise<ConversationRecord | null>;
  /** Insert or replace a record by its `id`. */
  put(record: ConversationRecord): Promise<void>;
  /**
   * Apply a metadata-only delta (rename / pin / archive) to `id`.
   *
   * OPTIONAL, and duck-typed by callers, because it only earns its keep where
   * more than one writer exists. A single-browser adapter (IndexedDB) has no
   * second writer to race, so `get → transform → put` is already correct there
   * and an extra verb would be ceremony. A shared backend does have one, and
   * there a whole-record put from a stale device silently drops flags it never
   * meant to touch — the delta is what makes that impossible.
   */
  patch?(id: string, patch: ConversationMetadataPatch): Promise<ConversationRecord | null>;
  /** Remove the record for `id` (no-op if absent). */
  delete(id: string): Promise<void>;
  /** Remove every stored conversation. */
  clear(): Promise<void>;
}
