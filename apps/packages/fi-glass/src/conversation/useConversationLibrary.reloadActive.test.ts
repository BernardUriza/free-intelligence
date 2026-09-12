// @vitest-environment jsdom
/**
 * useConversationLibrary — reloadActive (OG118-BACKGROUND-1).
 *
 * A background worker appends to the ACTIVE record server-side. The hook has
 * to adopt that append when asked, stay silent (no state churn) when nothing
 * moved, and treat a vanished record the way switchConversation does.
 */
import { describe, it, expect, vi } from 'vitest';
import { act, renderHook, waitFor } from '@testing-library/react';
import type {
  ChatMessage,
  ConversationLibrary,
  ConversationRecord,
  ConversationSummary,
} from '@free-intelligence/core';
import { summarizeConversation } from '@free-intelligence/core';
import { useConversationLibrary } from './useConversationLibrary';

const ID = 'conv-1';
const T0 = '2026-09-12T00:00:00.000Z';
const T1 = '2026-09-12T00:05:00.000Z';

function msg(role: ChatMessage['role'], content: string, timestamp = T0): ChatMessage {
  return { role, content, timestamp };
}

function seed(over: Partial<ConversationRecord> = {}): ConversationRecord {
  return {
    id: ID,
    title: 'hola',
    createdAt: T0,
    updatedAt: T0,
    messages: [msg('user', 'hola')],
    preview: 'hola',
    schemaVersion: 1,
    ...over,
  };
}

function makeLibrary(initial?: ConversationRecord) {
  const mem = new Map<string, ConversationRecord>();
  if (initial) mem.set(initial.id, initial);
  const list = vi.fn(
    async (): Promise<ConversationSummary[]> =>
      [...mem.values()]
        .map(summarizeConversation)
        .sort((a, b) => b.updatedAt.localeCompare(a.updatedAt)),
  );
  const library = {
    list,
    get: vi.fn(async (id: string) => mem.get(id) ?? null),
    put: vi.fn(async (r: ConversationRecord) => {
      mem.set(r.id, r);
    }),
    delete: vi.fn(async (id: string) => {
      mem.delete(id);
    }),
    clear: vi.fn(async () => {
      mem.clear();
    }),
  } as unknown as ConversationLibrary;
  return { library, mem, list };
}

function renderLib(library: ConversationLibrary) {
  return renderHook(() =>
    useConversationLibrary(library, { idFactory: () => ID, now: () => T0 }),
  );
}

describe('useConversationLibrary — reloadActive', () => {
  it('leaves state untouched when updatedAt did not move', async () => {
    const { library, list } = makeLibrary(seed());
    const { result } = renderLib(library);
    await waitFor(() => expect(result.current.ready).toBe(true));
    const before = result.current;
    const listCalls = list.mock.calls.length;

    await act(async () => {
      await result.current.reloadActive();
    });
    expect(result.current.activeRecord).toBe(before.activeRecord);
    expect(result.current.activeMessages).toBe(before.activeMessages);
    expect(list.mock.calls.length).toBe(listCalls);
  });

  it('adopts a server-side append and refreshes the list', async () => {
    const { library, mem, list } = makeLibrary(seed());
    const { result } = renderLib(library);
    await waitFor(() => expect(result.current.ready).toBe(true));
    expect(result.current.activeMessages).toHaveLength(1);

    // The worker's write: an assistant message, updatedAt + preview bumped.
    const appended = msg('assistant', 'listo, aquí está el reporte', T1);
    mem.set(ID, {
      ...seed(),
      messages: [msg('user', 'hola'), appended],
      updatedAt: T1,
      preview: appended.content,
    });
    const listCalls = list.mock.calls.length;

    await act(async () => {
      await result.current.reloadActive();
    });
    expect(result.current.activeMessages).toHaveLength(2);
    expect(result.current.activeMessages[1]).toEqual(appended);
    expect(result.current.activeRecord?.updatedAt).toBe(T1);
    expect(list.mock.calls.length).toBe(listCalls + 1);
    expect(result.current.conversations[0].preview).toBe(appended.content);
  });

  it('a stored record that vanished refreshes the list and throws like switchConversation', async () => {
    const { library, mem } = makeLibrary(seed());
    const { result } = renderLib(library);
    await waitFor(() => expect(result.current.ready).toBe(true));

    mem.delete(ID);
    await expect(result.current.reloadActive()).rejects.toThrow(/not found/);
    await waitFor(() => expect(result.current.conversations).toHaveLength(0));
  });

  it('a never-persisted conversation has nothing to reload and does not throw', async () => {
    const { library, list } = makeLibrary();
    const { result } = renderLib(library);
    await waitFor(() => expect(result.current.ready).toBe(true));
    expect(result.current.activeRecord).toBeNull();
    const listCalls = list.mock.calls.length;

    await act(async () => {
      await result.current.reloadActive();
    });
    expect(result.current.activeRecord).toBeNull();
    expect(list.mock.calls.length).toBe(listCalls);
  });
});
