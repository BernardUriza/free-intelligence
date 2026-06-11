// @vitest-environment jsdom
// AudioQueueStore — unit tests via a minimal in-memory IDBFactory stub.
// We mock the global indexedDB rather than pulling fake-indexeddb as a dep.

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { AudioQueueStore } from './AudioQueueStore';
import type { StoredAudioArtifact } from './audioArtifact';

// ---------------------------------------------------------------------------
// Minimal in-memory IndexedDB stub (just enough for AudioQueueStore)
// ---------------------------------------------------------------------------
function buildFakeIndexedDB() {
  const stores: Map<string, Map<string, StoredAudioArtifact>> = new Map();

  function getStore(name: string) {
    if (!stores.has(name)) stores.set(name, new Map());
    return stores.get(name)!;
  }

  function fakeRequest<T>(result: T): IDBRequest<T> {
    const req = {
      result,
      error: null,
      source: null,
      transaction: null,
      readyState: 'done' as IDBRequestReadyState,
      onsuccess: null as ((e: Event) => void) | null,
      onerror: null as ((e: Event) => void) | null,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    };
    queueMicrotask(() => req.onsuccess?.({} as Event));
    return req as unknown as IDBRequest<T>;
  }

  function makeObjectStore(storeName: string): IDBObjectStore {
    const mem = getStore(storeName);
    return {
      get: (key: string) => fakeRequest(mem.get(key)),
      getAll: () => fakeRequest([...mem.values()]),
      put: (val: StoredAudioArtifact) => {
        mem.set(val.id, val);
        return fakeRequest(undefined);
      },
      delete: (key: string) => {
        mem.delete(key);
        return fakeRequest(undefined);
      },
      clear: () => {
        mem.clear();
        return fakeRequest(undefined);
      },
      createIndex: vi.fn(),
    } as unknown as IDBObjectStore;
  }

  function makeTx(storeName: string): IDBTransaction {
    return {
      objectStore: () => makeObjectStore(storeName),
    } as unknown as IDBTransaction;
  }

  const fakeDB = {
    objectStoreNames: { contains: () => false },
    createObjectStore: (name: string) => makeObjectStore(name),
    transaction: (storeName: string) => makeTx(storeName),
  } as unknown as IDBDatabase;

  const fakeIndexedDB = {
    open: (_name: string, _version?: number): IDBOpenDBRequest => {
      const req = {
        result: fakeDB,
        error: null,
        source: null,
        transaction: makeTx('audio-artifacts'),
        readyState: 'done' as IDBRequestReadyState,
        onupgradeneeded: null as ((e: IDBVersionChangeEvent) => void) | null,
        onsuccess: null as ((e: Event) => void) | null,
        onerror: null as ((e: Event) => void) | null,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
        onblocked: null,
      };
      // Fire upgradeneeded then onsuccess
      queueMicrotask(() => {
        req.onupgradeneeded?.({
          target: req,
          oldVersion: 0,
          newVersion: 1,
        } as unknown as IDBVersionChangeEvent);
        req.onsuccess?.({} as Event);
      });
      return req as unknown as IDBOpenDBRequest;
    },
  } as unknown as IDBFactory;

  return fakeIndexedDB;
}

const artifact = (id: string, state: StoredAudioArtifact['state'] = 'queued'): StoredAudioArtifact => ({
  id,
  mime: 'audio/wav',
  size: 512,
  createdAt: '2026-06-11T00:00:00.000Z',
  updatedAt: '2026-06-11T00:00:00.000Z',
  state,
  blob: new Blob(['wav'], { type: 'audio/wav' }),
});

describe('AudioQueueStore', () => {
  let store: AudioQueueStore;

  beforeEach(() => {
    vi.stubGlobal('indexedDB', buildFakeIndexedDB());
    store = new AudioQueueStore();
  });

  it('list() empty initially', async () => {
    expect(await store.list()).toEqual([]);
  });

  it('put + get round-trip', async () => {
    await store.put(artifact('a1'));
    const r = await store.get('a1');
    expect(r?.id).toBe('a1');
    expect(r?.state).toBe('queued');
  });

  it('list() after two puts', async () => {
    await store.put(artifact('a1'));
    await store.put(artifact('a2', 'transcribed'));
    const list = await store.list();
    expect(list.map((x) => x.id).sort()).toEqual(['a1', 'a2']);
  });

  it('delete() removes artifact', async () => {
    await store.put(artifact('a1'));
    await store.delete('a1');
    expect(await store.get('a1')).toBeNull();
  });

  it('updateMeta() patches state without losing blob', async () => {
    await store.put(artifact('a1', 'queued'));
    await store.updateMeta('a1', { state: 'transcribed', transcript: 'hola' });
    const r = await store.get('a1');
    expect(r?.state).toBe('transcribed');
    expect(r?.transcript).toBe('hola');
    expect(r?.blob).toBeInstanceOf(Blob);
  });

  it('clear() empties the store', async () => {
    await store.put(artifact('a1'));
    await store.clear();
    expect(await store.list()).toHaveLength(0);
  });

  it('rejects when indexedDB is undefined', async () => {
    vi.stubGlobal('indexedDB', undefined);
    const s = new AudioQueueStore();
    await expect(s.list()).rejects.toThrow('IndexedDB');
  });
});
