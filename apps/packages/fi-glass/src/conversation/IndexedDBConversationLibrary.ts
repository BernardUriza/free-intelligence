/**
 * IndexedDBConversationLibrary — a browser ConversationLibrary (DD-002B1.2).
 *
 * Implements the @free-intelligence/core ConversationLibrary contract over
 * IndexedDB, zero external dependencies (a small promisified wrapper). This is
 * the first concrete adapter for the local-first transcript persistence the
 * core contract describes; later layers may add a backend adapter against the
 * SAME contract.
 *
 * Privacy: this adapter is a dumb store — it persists exactly the records it is
 * given. Sanitization (role/content/timestamp only, no tokens / metadata /
 * glass-box) happens upstream in core helpers, which the conversation hook uses
 * to build every record before `put`.
 *
 * SSR safety: the constructor never touches `indexedDB` (only stores config), so
 * instantiating during a server render is harmless. Any method that needs the DB
 * rejects with a CLEAR error when IndexedDB is unavailable (server render /
 * storage disabled) — it never fails silently.
 */

import type {
  ConversationLibrary,
  ConversationRecord,
  ConversationSummary,
} from '@free-intelligence/core';
import { summarizeConversation } from '@free-intelligence/core';

export interface IndexedDBConversationLibraryOptions {
  /** Database name. Default: `free-intelligence-conversations`. */
  dbName?: string;
  /** Object store name. Default: `conversations`. */
  storeName?: string;
}

const DEFAULT_DB_NAME = 'free-intelligence-conversations';
const DEFAULT_STORE_NAME = 'conversations';
const DB_VERSION = 1;
const UPDATED_AT_INDEX = 'by_updatedAt';

function indexedDBUnavailable(): boolean {
  return typeof indexedDB === 'undefined';
}

function unavailableError(): Error {
  return new Error(
    'IndexedDBConversationLibrary: IndexedDB is not available in this ' +
      'environment (server-side render or storage disabled). Use this adapter ' +
      'only in the browser.',
  );
}

export class IndexedDBConversationLibrary implements ConversationLibrary {
  private readonly dbName: string;
  private readonly storeName: string;
  private dbPromise: Promise<IDBDatabase> | null = null;

  constructor(options: IndexedDBConversationLibraryOptions = {}) {
    this.dbName = options.dbName ?? DEFAULT_DB_NAME;
    this.storeName = options.storeName ?? DEFAULT_STORE_NAME;
  }

  /** Open (and lazily create) the database. Rejects clearly if unavailable. */
  private open(): Promise<IDBDatabase> {
    if (indexedDBUnavailable()) return Promise.reject(unavailableError());
    if (!this.dbPromise) {
      this.dbPromise = new Promise<IDBDatabase>((resolve, reject) => {
        const request = indexedDB.open(this.dbName, DB_VERSION);
        request.onupgradeneeded = () => {
          const db = request.result;
          if (!db.objectStoreNames.contains(this.storeName)) {
            const store = db.createObjectStore(this.storeName, { keyPath: 'id' });
            store.createIndex(UPDATED_AT_INDEX, 'updatedAt', { unique: false });
          }
        };
        request.onsuccess = () => resolve(request.result);
        request.onerror = () =>
          reject(request.error ?? new Error('IndexedDB open failed'));
      });
    }
    return this.dbPromise;
  }

  /** Run one request inside a transaction and resolve with its result. */
  private async run<T>(
    mode: IDBTransactionMode,
    makeRequest: (store: IDBObjectStore) => IDBRequest,
  ): Promise<T> {
    const db = await this.open();
    return new Promise<T>((resolve, reject) => {
      const transaction = db.transaction(this.storeName, mode);
      const request = makeRequest(transaction.objectStore(this.storeName));
      request.onsuccess = () => resolve(request.result as T);
      request.onerror = () =>
        reject(request.error ?? new Error('IndexedDB request failed'));
    });
  }

  /** All conversations as light summaries, newest `updatedAt` first. */
  async list(): Promise<ConversationSummary[]> {
    const records = await this.run<ConversationRecord[]>('readonly', (store) =>
      store.getAll(),
    );
    return records
      .map(summarizeConversation)
      .sort((a, b) => b.updatedAt.localeCompare(a.updatedAt));
  }

  /** The full record for `id`, or `null` if none. */
  async get(id: string): Promise<ConversationRecord | null> {
    const record = await this.run<ConversationRecord | undefined>(
      'readonly',
      (store) => store.get(id),
    );
    return record ?? null;
  }

  /** Insert or replace a record by its `id`. */
  async put(record: ConversationRecord): Promise<void> {
    await this.run('readwrite', (store) => store.put(record));
  }

  /** Remove the record for `id` (no-op if absent). */
  async delete(id: string): Promise<void> {
    await this.run('readwrite', (store) => store.delete(id));
  }

  /** Remove every stored conversation. */
  async clear(): Promise<void> {
    await this.run('readwrite', (store) => store.clear());
  }
}
