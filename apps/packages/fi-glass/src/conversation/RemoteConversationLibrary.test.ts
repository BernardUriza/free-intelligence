/**
 * RemoteConversationLibrary + migrateConversationLibrary — the cloud adapter
 * honors the core ConversationLibrary contract (method↔endpoint mapping, 404→
 * null on get, loud errors otherwise, call-time headers) and the local→cloud
 * migration copies only what the target lacks, never touching the source.
 */
import { describe, it, expect, vi } from 'vitest';
import type {
  ConversationLibrary,
  ConversationRecord,
  ConversationSummary,
} from '@free-intelligence/core';

import { RemoteConversationLibrary } from './RemoteConversationLibrary';
import { migrateConversationLibrary } from './migrateConversationLibrary';

function record(id: string, updatedAt = '2026-07-08T00:00:00Z'): ConversationRecord {
  return {
    id,
    title: `Chat ${id}`,
    createdAt: '2026-07-08T00:00:00Z',
    updatedAt,
    messages: [{ id: 'm1', role: 'user', content: 'hola' } as never],
    preview: 'hola',
    schemaVersion: 1,
  };
}

function jsonResponse(status: number, body?: unknown): Response {
  return new Response(body === undefined ? null : JSON.stringify(body), { status });
}

function makeLibrary(fetchImpl: typeof fetch, headers?: () => Record<string, string>) {
  return new RemoteConversationLibrary({
    baseUrl: 'https://api.test/',
    fetchImpl,
    headers,
  });
}

describe('RemoteConversationLibrary', () => {
  it('list GETs /conversations with call-time headers and unwraps the payload', async () => {
    const summaries: ConversationSummary[] = [
      { id: 'a', title: 'A', createdAt: 'x', updatedAt: 'y', preview: 'p' },
    ];
    const fetchImpl = vi.fn(async (_input: RequestInfo | URL, _init?: RequestInit) => jsonResponse(200, { conversations: summaries }));
    let token = 'tok-1';
    const lib = makeLibrary(fetchImpl as never, () => ({ Authorization: `Bearer ${token}` }));

    await expect(lib.list()).resolves.toEqual(summaries);
    token = 'tok-2';
    await lib.list();

    expect(fetchImpl).toHaveBeenNthCalledWith(
      1,
      'https://api.test/conversations',
      expect.objectContaining({
        method: 'GET',
        headers: { Authorization: 'Bearer tok-1' },
      }),
    );
    expect(fetchImpl.mock.calls[1]?.[1]).toMatchObject({
      headers: { Authorization: 'Bearer tok-2' },
    });
  });

  it('get returns the record, null on 404, and throws loud otherwise', async () => {
    const rec = record('conv-1');
    const fetchImpl = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(200, rec))
      .mockResolvedValueOnce(jsonResponse(404))
      .mockResolvedValueOnce(jsonResponse(500));
    const lib = makeLibrary(fetchImpl as never);

    await expect(lib.get('conv-1')).resolves.toEqual(rec);
    await expect(lib.get('conv-2')).resolves.toBeNull();
    await expect(lib.get('conv-3')).rejects.toThrow('HTTP 500');
    expect(fetchImpl.mock.calls[0]?.[0]).toBe('https://api.test/conversations/conv-1');
  });

  it('put PUTs the record as JSON to its id path and throws on failure', async () => {
    const rec = record('conv-1');
    const fetchImpl = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse(200, { id: 'conv-1' }))
      .mockResolvedValueOnce(jsonResponse(413));
    const lib = makeLibrary(fetchImpl as never);

    await lib.put(rec);
    expect(fetchImpl).toHaveBeenCalledWith(
      'https://api.test/conversations/conv-1',
      expect.objectContaining({
        method: 'PUT',
        body: JSON.stringify(rec),
        headers: expect.objectContaining({ 'Content-Type': 'application/json' }),
      }),
    );
    await expect(lib.put(rec)).rejects.toThrow('HTTP 413');
  });

  it('delete and clear hit their endpoints', async () => {
    const fetchImpl = vi.fn(async (_input: RequestInfo | URL, _init?: RequestInit) => jsonResponse(200, {}));
    const lib = makeLibrary(fetchImpl as never);

    await lib.delete('conv 1');
    await lib.clear();

    expect(fetchImpl.mock.calls[0]?.[0]).toBe('https://api.test/conversations/conv%201');
    expect(fetchImpl.mock.calls[0]?.[1]).toMatchObject({ method: 'DELETE' });
    expect(fetchImpl.mock.calls[1]?.[0]).toBe('https://api.test/conversations');
    expect(fetchImpl.mock.calls[1]?.[1]).toMatchObject({ method: 'DELETE' });
  });
});

function memoryLibrary(seed: ConversationRecord[] = []): ConversationLibrary & {
  mem: Map<string, ConversationRecord>;
} {
  const mem = new Map(seed.map((r) => [r.id, r]));
  return {
    mem,
    list: async () =>
      [...mem.values()].map(({ id, title, createdAt, updatedAt, preview }) => ({
        id,
        title,
        createdAt,
        updatedAt,
        preview,
      })),
    get: async (id) => mem.get(id) ?? null,
    put: async (r) => void mem.set(r.id, r),
    delete: async (id) => void mem.delete(id),
    clear: async () => void mem.clear(),
  };
}

describe('migrateConversationLibrary', () => {
  it('copies missing records, skips collisions (target wins), source untouched', async () => {
    const localOnly = record('local-1');
    const shared = record('shared', '2026-07-01T00:00:00Z');
    const sharedNewer = record('shared', '2026-07-08T00:00:00Z');
    const source = memoryLibrary([localOnly, shared]);
    const target = memoryLibrary([sharedNewer]);

    const result = await migrateConversationLibrary(source, target);

    expect(result).toEqual({ migrated: 1, skipped: 1 });
    expect(target.mem.get('local-1')).toEqual(localOnly);
    expect(target.mem.get('shared')).toEqual(sharedNewer);
    expect(source.mem.size).toBe(2);
  });

  it('is idempotent', async () => {
    const source = memoryLibrary([record('a'), record('b')]);
    const target = memoryLibrary();

    await migrateConversationLibrary(source, target);
    const second = await migrateConversationLibrary(source, target);

    expect(second).toEqual({ migrated: 0, skipped: 2 });
    expect(target.mem.size).toBe(2);
  });
});
