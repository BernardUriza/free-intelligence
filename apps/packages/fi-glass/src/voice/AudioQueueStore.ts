// B3-VOICE-FIGLASS-9 — IndexedDB store for durable audio artifacts.
// Follows the exact pattern of IndexedDBConversationLibrary. Constructor never
// touches indexedDB, so server-side instantiation is safe. Methods reject clearly
// when IndexedDB is unavailable — no silent failures.

import type { StoredAudioArtifact, AudioArtifact } from './audioArtifact';

export interface AudioQueueStoreOptions {
  dbName?: string;
  storeName?: string;
}

const DEFAULT_DB_NAME = 'free-intelligence-audio-queue';
const DEFAULT_STORE_NAME = 'audio-artifacts';
const DB_VERSION = 1;
const CREATED_AT_INDEX = 'by_createdAt';

function unavailable(): boolean {
  return typeof indexedDB === 'undefined';
}

function unavailableError(): Error {
  return new Error(
    'AudioQueueStore: IndexedDB is not available (SSR or storage disabled).',
  );
}

export class AudioQueueStore {
  private readonly dbName: string;
  private readonly storeName: string;
  private dbPromise: Promise<IDBDatabase> | null = null;

  constructor(opts: AudioQueueStoreOptions = {}) {
    this.dbName = opts.dbName ?? DEFAULT_DB_NAME;
    this.storeName = opts.storeName ?? DEFAULT_STORE_NAME;
  }

  private open(): Promise<IDBDatabase> {
    if (unavailable()) return Promise.reject(unavailableError());
    if (!this.dbPromise) {
      this.dbPromise = new Promise<IDBDatabase>((resolve, reject) => {
        const req = indexedDB.open(this.dbName, DB_VERSION);
        req.onupgradeneeded = () => {
          const db = req.result;
          if (!db.objectStoreNames.contains(this.storeName)) {
            const store = db.createObjectStore(this.storeName, { keyPath: 'id' });
            store.createIndex(CREATED_AT_INDEX, 'createdAt', { unique: false });
          }
        };
        req.onsuccess = () => resolve(req.result);
        req.onerror = () =>
          reject(req.error ?? new Error('AudioQueueStore: open failed'));
      });
    }
    return this.dbPromise;
  }

  private async run<T>(
    mode: IDBTransactionMode,
    makeRequest: (store: IDBObjectStore) => IDBRequest,
  ): Promise<T> {
    const db = await this.open();
    return new Promise<T>((resolve, reject) => {
      const tx = db.transaction(this.storeName, mode);
      const req = makeRequest(tx.objectStore(this.storeName));
      req.onsuccess = () => resolve(req.result as T);
      req.onerror = () =>
        reject(req.error ?? new Error('AudioQueueStore: request failed'));
    });
  }

  async list(): Promise<StoredAudioArtifact[]> {
    return this.run<StoredAudioArtifact[]>('readonly', (s) => s.getAll());
  }

  async get(id: string): Promise<StoredAudioArtifact | null> {
    const r = await this.run<StoredAudioArtifact | undefined>(
      'readonly',
      (s) => s.get(id),
    );
    return r ?? null;
  }

  async put(artifact: StoredAudioArtifact): Promise<void> {
    await this.run('readwrite', (s) => s.put(artifact));
  }

  async updateMeta(
    id: string,
    patch: Partial<Omit<AudioArtifact, 'id' | 'blob'>>,
  ): Promise<void> {
    const existing = await this.get(id);
    if (!existing) return;
    await this.put({
      ...existing,
      ...patch,
      id,
      updatedAt: new Date().toISOString(),
    });
  }

  async delete(id: string): Promise<void> {
    await this.run('readwrite', (s) => s.delete(id));
  }

  async clear(): Promise<void> {
    await this.run('readwrite', (s) => s.clear());
  }
}
