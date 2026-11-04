// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from 'vitest';
import { act, renderHook, waitFor } from '@testing-library/react';
import type { ConversationLibrary, ConversationRecord } from '@free-intelligence/core';
import { EphemeralConversationLibrary } from './EphemeralConversationLibrary';
import { useCloudConversationLibrary } from './useCloudConversationLibrary';

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

function flakyRemote(): ConversationLibrary & { down: boolean; gate: Promise<void> | null } {
  const store = new EphemeralConversationLibrary();
  const remote = {
    down: false,
    gate: null as Promise<void> | null,
    async list() {
      if (remote.gate) await remote.gate;
      if (remote.down) throw new Error('503');
      return store.list();
    },
    get: (id: string) => store.get(id),
    put: (r: ConversationRecord) => store.put(r),
    delete: (id: string) => store.delete(id),
  };
  return remote as unknown as ConversationLibrary & { down: boolean; gate: Promise<void> | null };
}

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe('useCloudConversationLibrary', () => {
  it('stays local and says so when the account is not signed in', () => {
    const local = new EphemeralConversationLibrary();
    const remote = flakyRemote();
    const { result } = renderHook(() =>
      useCloudConversationLibrary({ local, remote, enabled: false, scopeKey: null }),
    );
    expect(result.current.status).toBe('local');
    expect(result.current.library).toBe(local);
  });

  it('reports connecting, then slow, while a cold server answers — never "local"', async () => {
    vi.useFakeTimers();
    const local = new EphemeralConversationLibrary();
    const remote = flakyRemote();
    let open!: () => void;
    remote.gate = new Promise((r) => (open = r));
    const { result } = renderHook(() =>
      useCloudConversationLibrary({ local, remote, enabled: true, scopeKey: 'u1', slowAfterMs: 4000 }),
    );
    expect(result.current.status).toBe('connecting');
    expect(result.current.slow).toBe(false);
    await act(async () => {
      vi.advanceTimersByTime(4000);
    });
    expect(result.current.slow).toBe(true);
    remote.gate = null;
    await act(async () => {
      open();
    });
    vi.useRealTimers();
    await waitFor(() => expect(result.current.status).toBe('cloud'));
    expect(result.current.library).toBe(remote);
    expect(result.current.slow).toBe(false);
  });

  it('falls to unreachable, retries on its own, and uploads what was written offline', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
    const local = new EphemeralConversationLibrary();
    const remote = flakyRemote();
    remote.down = true;
    const { result } = renderHook(() =>
      useCloudConversationLibrary({
        local,
        remote,
        enabled: true,
        scopeKey: 'u1',
        retryDelaysMs: [20],
      }),
    );
    await waitFor(() => expect(result.current.status).toBe('unreachable'));
    expect(result.current.library).toBe(local);

    await local.put(record('written-offline'));
    remote.down = false;

    await waitFor(() => expect(result.current.status).toBe('cloud'));
    expect((await remote.get('written-offline'))?.id).toBe('written-offline');
  });

  it('a manual retry shows connecting again instead of a stale "unreachable"', async () => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
    const local = new EphemeralConversationLibrary();
    const remote = flakyRemote();
    remote.down = true;
    const { result } = renderHook(() =>
      useCloudConversationLibrary({
        local,
        remote,
        enabled: true,
        scopeKey: 'u1',
        retryDelaysMs: [60_000],
      }),
    );
    await waitFor(() => expect(result.current.status).toBe('unreachable'));
    let open!: () => void;
    remote.gate = new Promise((r) => (open = r));
    remote.down = false;
    act(() => result.current.retry());
    expect(result.current.status).toBe('connecting');
    remote.gate = null;
    await act(async () => {
      open();
    });
    await waitFor(() => expect(result.current.status).toBe('cloud'));
  });

  it('a different account starts over instead of inheriting the previous one\'s cloud', async () => {
    const local = new EphemeralConversationLibrary();
    const remote = flakyRemote();
    const { result, rerender } = renderHook(
      ({ scopeKey }) => useCloudConversationLibrary({ local, remote, enabled: true, scopeKey }),
      { initialProps: { scopeKey: 'u1' } },
    );
    await waitFor(() => expect(result.current.status).toBe('cloud'));
    rerender({ scopeKey: 'u2' });
    expect(result.current.status).toBe('connecting');
    await waitFor(() => expect(result.current.status).toBe('cloud'));
  });
});
