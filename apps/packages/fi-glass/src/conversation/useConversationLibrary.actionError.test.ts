// @vitest-environment jsdom
import { describe, it, expect } from 'vitest';
import { act, renderHook, waitFor } from '@testing-library/react';
import type { ConversationLibrary, ConversationRecord } from '@free-intelligence/core';
import { EphemeralConversationLibrary } from './EphemeralConversationLibrary';
import { useConversationLibrary } from './useConversationLibrary';

const T0 = '2026-10-09T00:00:00.000Z';

function record(id: string): ConversationRecord {
  return {
    id,
    title: id,
    createdAt: T0,
    updatedAt: T0,
    messages: [{ role: 'user', content: id, timestamp: T0 }],
    preview: id,
    schemaVersion: 1,
  };
}

function breakable(store: EphemeralConversationLibrary) {
  const lib = {
    down: false,
    list: () => store.list(),
    get: (id: string) => store.get(id),
    put: (r: ConversationRecord) => store.put(r),
    async delete(id: string) {
      if (lib.down) throw new Error('503 Service Unavailable');
      return store.delete(id);
    },
  };
  return lib as typeof lib & ConversationLibrary;
}

async function mounted() {
  const store = new EphemeralConversationLibrary();
  await store.put(record('a'));
  await store.put(record('b'));
  const library = breakable(store);
  const hook = renderHook(() => useConversationLibrary(library));
  await waitFor(() => expect(hook.result.current.ready).toBe(true));
  return { library, store, hook };
}

describe('useConversationLibrary — action errors are visible state', () => {
  it('a failed delete becomes actionError instead of vanishing into a console', async () => {
    const { library, hook } = await mounted();
    library.down = true;
    await act(async () => {
      await hook.result.current.deleteConversation('a').catch(() => {});
    });
    expect(hook.result.current.actionError).toMatchObject({
      action: 'delete',
      conversationId: 'a',
      message: '503 Service Unavailable',
    });
    expect(hook.result.current.conversations.map((c) => c.id)).toContain('a');
  });

  it('retryAction re-runs exactly the failed action and clears the error on success', async () => {
    const { library, hook } = await mounted();
    library.down = true;
    await act(async () => {
      await hook.result.current.deleteConversation('a').catch(() => {});
    });
    library.down = false;
    act(() => hook.result.current.retryAction());
    await waitFor(() =>
      expect(hook.result.current.conversations.map((c) => c.id)).not.toContain('a'),
    );
    expect(hook.result.current.actionError).toBeNull();
  });

  it('a switch to a conversation deleted elsewhere is reported, not swallowed', async () => {
    const { store, hook } = await mounted();
    await store.delete('b');
    await act(async () => {
      await hook.result.current.switchConversation('b').catch(() => {});
    });
    expect(hook.result.current.actionError?.action).toBe('switch');
  });

  it('dismiss forgets the failed action so a later retry is a no-op', async () => {
    const { library, hook } = await mounted();
    library.down = true;
    await act(async () => {
      await hook.result.current.deleteConversation('a').catch(() => {});
    });
    act(() => hook.result.current.dismissActionError());
    library.down = false;
    act(() => hook.result.current.retryAction());
    expect(hook.result.current.actionError).toBeNull();
    expect(hook.result.current.conversations.map((c) => c.id)).toContain('a');
  });
});
