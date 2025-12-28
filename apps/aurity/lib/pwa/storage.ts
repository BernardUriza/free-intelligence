// =============================================================================
// PWA Offline Storage Utilities
// =============================================================================
// IndexedDB wrapper for offline data persistence
// =============================================================================

const DB_NAME = 'aurity-pwa';
const DB_VERSION = 1;

// Store names
export const STORES = {
  OFFLINE_QUEUE: 'offline-queue',
  CACHED_DATA: 'cached-data',
  USER_PREFERENCES: 'user-preferences',
} as const;

type StoreName = (typeof STORES)[keyof typeof STORES];

// Open database connection
function openDB(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);

    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result);

    request.onupgradeneeded = (event) => {
      const db = (event.target as IDBOpenDBRequest).result;

      // Create stores if they don't exist
      if (!db.objectStoreNames.contains(STORES.OFFLINE_QUEUE)) {
        db.createObjectStore(STORES.OFFLINE_QUEUE, { keyPath: 'id', autoIncrement: true });
      }

      if (!db.objectStoreNames.contains(STORES.CACHED_DATA)) {
        const store = db.createObjectStore(STORES.CACHED_DATA, { keyPath: 'key' });
        store.createIndex('timestamp', 'timestamp', { unique: false });
      }

      if (!db.objectStoreNames.contains(STORES.USER_PREFERENCES)) {
        db.createObjectStore(STORES.USER_PREFERENCES, { keyPath: 'key' });
      }
    };
  });
}

// Generic CRUD operations
export async function dbGet<T>(store: StoreName, key: string): Promise<T | undefined> {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const transaction = db.transaction(store, 'readonly');
    const objectStore = transaction.objectStore(store);
    const request = objectStore.get(key);

    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result as T | undefined);
  });
}

export async function dbSet<T>(store: StoreName, data: T): Promise<void> {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const transaction = db.transaction(store, 'readwrite');
    const objectStore = transaction.objectStore(store);
    const request = objectStore.put(data);

    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve();
  });
}

export async function dbDelete(store: StoreName, key: string): Promise<void> {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const transaction = db.transaction(store, 'readwrite');
    const objectStore = transaction.objectStore(store);
    const request = objectStore.delete(key);

    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve();
  });
}

export async function dbGetAll<T>(store: StoreName): Promise<T[]> {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const transaction = db.transaction(store, 'readonly');
    const objectStore = transaction.objectStore(store);
    const request = objectStore.getAll();

    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result as T[]);
  });
}

export async function dbClear(store: StoreName): Promise<void> {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const transaction = db.transaction(store, 'readwrite');
    const objectStore = transaction.objectStore(store);
    const request = objectStore.clear();

    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve();
  });
}

// =============================================================================
// Offline Queue - For syncing actions when back online
// =============================================================================

export interface QueuedAction {
  id?: number;
  type: string;
  payload: unknown;
  timestamp: number;
  retries: number;
}

export async function queueAction(type: string, payload: unknown): Promise<void> {
  const action: QueuedAction = {
    type,
    payload,
    timestamp: Date.now(),
    retries: 0,
  };
  await dbSet(STORES.OFFLINE_QUEUE, action);
  console.log('[PWA] Action queued for sync:', type);
}

export async function getQueuedActions(): Promise<QueuedAction[]> {
  return dbGetAll<QueuedAction>(STORES.OFFLINE_QUEUE);
}

export async function removeQueuedAction(id: number): Promise<void> {
  await dbDelete(STORES.OFFLINE_QUEUE, String(id));
}

export async function clearQueue(): Promise<void> {
  await dbClear(STORES.OFFLINE_QUEUE);
}

// =============================================================================
// Cached Data - For offline-first data access
// =============================================================================

export interface CachedItem<T> {
  key: string;
  data: T;
  timestamp: number;
  ttl?: number; // Time to live in milliseconds
}

export async function cacheData<T>(key: string, data: T, ttl?: number): Promise<void> {
  const item: CachedItem<T> = {
    key,
    data,
    timestamp: Date.now(),
    ttl,
  };
  await dbSet(STORES.CACHED_DATA, item);
}

export async function getCachedData<T>(key: string): Promise<T | null> {
  const item = await dbGet<CachedItem<T>>(STORES.CACHED_DATA, key);

  if (!item) return null;

  // Check if expired
  if (item.ttl && Date.now() - item.timestamp > item.ttl) {
    await dbDelete(STORES.CACHED_DATA, key);
    return null;
  }

  return item.data;
}

export async function invalidateCache(key: string): Promise<void> {
  await dbDelete(STORES.CACHED_DATA, key);
}

// =============================================================================
// User Preferences - Persistent user settings
// =============================================================================

export interface UserPreference {
  key: string;
  value: unknown;
}

export async function setPreference(key: string, value: unknown): Promise<void> {
  await dbSet(STORES.USER_PREFERENCES, { key, value });
}

export async function getPreference<T>(key: string, defaultValue: T): Promise<T> {
  const pref = await dbGet<UserPreference>(STORES.USER_PREFERENCES, key);
  return (pref?.value as T) ?? defaultValue;
}
