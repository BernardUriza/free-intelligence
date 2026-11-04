// @vitest-environment jsdom
import { describe, it, expect } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import type { ConversationLibrary, ConversationRecord } from '@free-intelligence/core';
import { summarizeConversation } from '@free-intelligence/core';
import { useConversationLibrary } from './useConversationLibrary';

const NOW = '2026-10-09T12:00:00.000Z';
const LATER = '2026-10-09T13:00:00.000Z';

const record = (id: string, extra: Partial<ConversationRecord> = {}): ConversationRecord => ({
  id,
  title: id,
  createdAt: NOW,
  updatedAt: NOW,
  messages: [{ role: 'user', content: id, timestamp: NOW }],
  preview: id,
  schemaVersion: 1,
  ...extra,
});

function store(...records: ConversationRecord[]): ConversationLibrary {
  const mem = new Map(records.map((r) => [r.id, r]));
  return {
    list: async () =>
      [...mem.values()].map(summarizeConversation).sort((a, b) => b.updatedAt.localeCompare(a.updatedAt)),
    get: async (id) => mem.get(id) ?? null,
    put: async (r) => void mem.set(r.id, r),
    delete: async (id) => void mem.delete(id),
    clear: async () => mem.clear(),
  };
}

describe('useConversationLibrary — what opens on load', () => {
  it('never opens an archived chat by default (all archived → a fresh chat)', async () => {
    const lib = store(record('a', { archivedAt: LATER, updatedAt: LATER }), record('b', { archivedAt: NOW }));
    const { result } = renderHook(() => useConversationLibrary(lib, { idFactory: () => 'fresh' }));
    await waitFor(() => expect(result.current.ready).toBe(true));
    expect(result.current.activeId).toBe('fresh');
    expect(result.current.activeMessages).toEqual([]);
  });

  it('skips archived chats when picking the most recent', async () => {
    const lib = store(record('archived', { archivedAt: LATER, updatedAt: LATER }), record('live'));
    const { result } = renderHook(() => useConversationLibrary(lib));
    await waitFor(() => expect(result.current.activeId).toBe('live'));
  });

  it('routed to /: a fresh chat even when there are recent ones', async () => {
    const lib = store(record('recent'));
    const { result } = renderHook(() =>
      useConversationLibrary(lib, { initialActiveId: null, idFactory: () => 'fresh' }),
    );
    await waitFor(() => expect(result.current.ready).toBe(true));
    expect(result.current.activeId).toBe('fresh');
    expect(result.current.activeMessages).toEqual([]);
  });

  it('routed to /c/<id>: opens exactly that chat, archived or not', async () => {
    const lib = store(record('recent', { updatedAt: LATER }), record('wanted', { archivedAt: NOW }));
    const { result } = renderHook(() => useConversationLibrary(lib, { initialActiveId: 'wanted' }));
    await waitFor(() => expect(result.current.activeMessages.map((m) => m.content)).toEqual(['wanted']));
    expect(result.current.activeId).toBe('wanted');
  });
});
