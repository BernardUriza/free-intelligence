// @vitest-environment jsdom
import { describe, it, expect, vi } from 'vitest';
import { act, renderHook, waitFor } from '@testing-library/react';
import type {
  ConversationLibrary,
  ConversationMetadataPatch,
  ConversationRecord,
} from '@free-intelligence/core';
import { applyConversationMetadataPatch, summarizeConversation } from '@free-intelligence/core';
import { useConversationLibrary } from './useConversationLibrary';

const NOW = '2026-10-09T12:00:00.000Z';

const record = (id: string, pinnedAt?: string): ConversationRecord => ({
  id,
  title: id,
  createdAt: NOW,
  updatedAt: NOW,
  messages: [{ role: 'user', content: id, timestamp: NOW }],
  preview: id,
  schemaVersion: 1,
  ...(pinnedAt ? { pinnedAt } : {}),
});

function cloudLibrary(records: ConversationRecord[], failOn: string[] = []) {
  const mem = new Map(records.map((r) => [r.id, r]));
  const patch = vi.fn(async (id: string, delta: ConversationMetadataPatch) => {
    if (failOn.includes(id)) throw new Error('500');
    const stored = mem.get(id);
    if (!stored) return null;
    const next = applyConversationMetadataPatch(stored, delta);
    mem.set(id, next);
    return next;
  });
  const list = vi.fn(async () => [...mem.values()].map(summarizeConversation));
  const library: ConversationLibrary = {
    list,
    get: async (id) => mem.get(id) ?? null,
    put: async (r) => void mem.set(r.id, r),
    delete: async (id) => void mem.delete(id),
    clear: async () => mem.clear(),
    patch,
  };
  return { library, mem, patch, list };
}

describe('useConversationLibrary.archiveConversations', () => {
  it('archives every id, clears pins, and refreshes the list once for the batch', async () => {
    const { library, mem, list } = cloudLibrary([record('a'), record('b', NOW), record('c')]);
    const { result } = renderHook(() => useConversationLibrary(library));
    await waitFor(() => expect(result.current.ready).toBe(true));
    const listsBefore = list.mock.calls.length;

    let failed: string[] = [];
    await act(async () => {
      failed = await result.current.archiveConversations(['a', 'b', 'c']);
    });

    expect(failed).toEqual([]);
    for (const id of ['a', 'b', 'c']) expect(mem.get(id)?.archivedAt).toBeTruthy();
    expect(mem.get('b')?.pinnedAt).toBeFalsy();
    expect(list.mock.calls.length - listsBefore).toBe(1);
    expect(result.current.conversations.every((c) => c.archivedAt)).toBe(true);
  });

  it('never throws: resolves with the ids that failed and archives the rest', async () => {
    const { library, mem } = cloudLibrary([record('a'), record('b'), record('c')], ['b']);
    const { result } = renderHook(() => useConversationLibrary(library));
    await waitFor(() => expect(result.current.ready).toBe(true));

    let failed: string[] = [];
    await act(async () => {
      failed = await result.current.archiveConversations(['a', 'b', 'c', 'gone']);
    });

    expect(failed.sort()).toEqual(['b', 'gone']);
    expect(mem.get('a')?.archivedAt).toBeTruthy();
    expect(mem.get('b')?.archivedAt).toBeFalsy();
    expect(mem.get('c')?.archivedAt).toBeTruthy();
  });
});
