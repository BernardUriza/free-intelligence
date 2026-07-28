/**
 * EphemeralConversationLibrary — conversations that die with the tab.
 *
 * The ConversationLibrary contract satisfied by a plain in-memory Map: nothing
 * reaches IndexedDB, localStorage or a server, and closing the tab is the whole
 * cleanup story.
 *
 * It exists for **shared-machine / kiosk surfaces**, where persistence is not a
 * missing feature but a hazard: a public terminal that remembers threads shows
 * the previous stranger's conversation to the next one. IndexedDB is the wrong
 * tool there (it is per-browser, not per-person, so every visitor inherits the
 * last one's history), and a remote library is worse (it publishes it).
 *
 * The live thread still works exactly as anywhere else — messages, streaming,
 * switching between conversations opened during this visit — because the
 * contract is the same. What disappears is only what should: everything, on
 * close.
 *
 * @example
 * const library = useMemo(
 *   () => (isPublicTerminal ? new EphemeralConversationLibrary() : remote),
 *   [isPublicTerminal, remote],
 * );
 * const lib = useConversationLibrary(library);
 */

import type {
  ConversationLibrary,
  ConversationRecord,
  ConversationSummary,
} from '@free-intelligence/core';

export class EphemeralConversationLibrary implements ConversationLibrary {
  private readonly records = new Map<string, ConversationRecord>();

  async list(): Promise<ConversationSummary[]> {
    return [...this.records.values()]
      .map(({ messages: _messages, ...summary }) => summary as ConversationSummary)
      .sort((a, b) => b.updatedAt.localeCompare(a.updatedAt));
  }

  async get(id: string): Promise<ConversationRecord | null> {
    const found = this.records.get(id);
    // A structural copy, so a consumer mutating what it read cannot reach back
    // into the store — the same isolation a real storage round-trip gives for
    // free, and without it the two adapters would behave differently.
    return found ? structuredClone(found) : null;
  }

  async put(record: ConversationRecord): Promise<void> {
    this.records.set(record.id, structuredClone(record));
  }

  async delete(id: string): Promise<void> {
    this.records.delete(id);
  }

  async clear(): Promise<void> {
    this.records.clear();
  }
}
