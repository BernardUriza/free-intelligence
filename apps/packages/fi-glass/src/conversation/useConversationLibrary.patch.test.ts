// @vitest-environment jsdom
/**
 * useConversationLibrary — the metadata seam prefers the DELTA (CONV-CONCURRENCY-1).
 *
 * A store shared by two devices cannot be mutated with whole records: whichever
 * side holds the older copy rewrites the flags it never knew about, and a pin
 * vanishes with nothing failing. So when the backing library offers `patch`, the
 * hook must send the delta and adopt the store's merged answer — never its own
 * optimistic guess, which is precisely the stale thing.
 *
 * A single-browser library has no second writer, so it keeps the read-apply-write
 * path and needs no extra verb.
 */
import { describe, it, expect, vi } from 'vitest';
import { act, renderHook, waitFor } from '@testing-library/react';
import type {
  ConversationLibrary,
  ConversationMetadataPatch,
  ConversationRecord,
  ConversationSummary,
} from '@free-intelligence/core';
import {
  applyConversationMetadataPatch,
  summarizeConversation,
} from '@free-intelligence/core';
import { useConversationLibrary } from './useConversationLibrary';

const ID = 'conv-1';
const NOW = '2026-08-23T00:00:00.000Z';

function seed(over: Partial<ConversationRecord> = {}): ConversationRecord {
  return {
    id: ID,
    title: 'Hola',
    createdAt: NOW,
    updatedAt: NOW,
    messages: [{ role: 'user', content: 'hola', timestamp: NOW }],
    preview: 'hola',
    schemaVersion: 1,
    ...over,
  };
}

/** A store with a `patch` verb — the cloud shape. */
function makeSharedLibrary(initial: ConversationRecord) {
  const mem = new Map<string, ConversationRecord>([[initial.id, initial]]);
  const patch = vi.fn(
    async (id: string, delta: ConversationMetadataPatch) => {
      const stored = mem.get(id);
      if (!stored) return null;
      const next = applyConversationMetadataPatch(stored, delta);
      mem.set(id, next);
      return next;
    },
  );
  const put = vi.fn(async (r: ConversationRecord) => {
    mem.set(r.id, r);
  });
  const library = {
    list: vi.fn(
      async (): Promise<ConversationSummary[]> =>
        [...mem.values()].map(summarizeConversation),
    ),
    get: vi.fn(async (id: string) => mem.get(id) ?? null),
    put,
    patch,
    delete: vi.fn(async () => {}),
    clear: vi.fn(async () => {}),
  } as unknown as ConversationLibrary;
  return { library, patch, put, mem };
}

/** A store WITHOUT `patch` — the single-browser shape. */
function makeLocalLibrary(initial: ConversationRecord) {
  const mem = new Map<string, ConversationRecord>([[initial.id, initial]]);
  const put = vi.fn(async (r: ConversationRecord) => {
    mem.set(r.id, r);
  });
  const library = {
    list: vi.fn(
      async (): Promise<ConversationSummary[]> =>
        [...mem.values()].map(summarizeConversation),
    ),
    get: vi.fn(async (id: string) => mem.get(id) ?? null),
    put,
    delete: vi.fn(async () => {}),
    clear: vi.fn(async () => {}),
  } as unknown as ConversationLibrary;
  return { library, put, mem };
}

function renderLib(library: ConversationLibrary) {
  return renderHook(() =>
    useConversationLibrary(library, { idFactory: () => ID, now: () => NOW }),
  );
}

describe('metadata mutations over a shared store', () => {
  it('pins by sending the delta, never the record', async () => {
    const { library, patch, put } = makeSharedLibrary(seed());
    const { result } = renderLib(library);
    await waitFor(() => expect(result.current.ready).toBe(true));

    await act(async () => {
      await result.current.pinConversation(ID, true);
    });

    expect(patch).toHaveBeenCalledWith(ID, {
      pinnedAt: NOW,
      archivedAt: null,
    });
    expect(put).not.toHaveBeenCalled();
  });

  it('archives and renames through the same seam', async () => {
    const { library, patch } = makeSharedLibrary(seed());
    const { result } = renderLib(library);
    await waitFor(() => expect(result.current.ready).toBe(true));

    await act(async () => {
      await result.current.archiveConversation(ID, true);
    });
    expect(patch).toHaveBeenCalledWith(ID, { archivedAt: NOW, pinnedAt: null });

    await act(async () => {
      await result.current.renameConversation(ID, 'Presupuesto');
    });
    expect(patch).toHaveBeenCalledWith(ID, {
      title: 'Presupuesto',
      titleCustom: true,
      updatedAt: NOW,
    });
  });

  it('adopts the STORE\'s merged record, not its own guess', async () => {
    // The store returns something the caller did not ask for — here, a title
    // another device renamed to. The hook must show that, because the store is
    // the authority and the local copy is by definition the stale one.
    const { library } = makeSharedLibrary(seed());
    (library as unknown as { patch: unknown }).patch = vi.fn(async () => ({
      ...seed({ title: 'Renombrado en el teléfono' }),
      pinnedAt: NOW,
    }));
    const { result } = renderLib(library);
    await waitFor(() => expect(result.current.ready).toBe(true));

    await act(async () => {
      await result.current.pinConversation(ID, true);
    });

    expect(result.current.activeRecord?.title).toBe('Renombrado en el teléfono');
  });

  it('surfaces a conversation deleted from the other device', async () => {
    const { library } = makeSharedLibrary(seed());
    (library as unknown as { patch: unknown }).patch = vi.fn(async () => null);
    const { result } = renderLib(library);
    await waitFor(() => expect(result.current.ready).toBe(true));

    await expect(
      act(async () => {
        await result.current.pinConversation(ID, true);
      }),
    ).rejects.toThrow(/not found/);
  });
});

describe('metadata mutations over a single-browser store', () => {
  it('falls back to read-apply-write when there is no patch verb', async () => {
    const { library, put, mem } = makeLocalLibrary(seed());
    const { result } = renderLib(library);
    await waitFor(() => expect(result.current.ready).toBe(true));

    await act(async () => {
      await result.current.pinConversation(ID, true);
    });

    expect(put).toHaveBeenCalledTimes(1);
    expect(mem.get(ID)?.pinnedAt).toBe(NOW);
  });

  it('unpins by dropping the field, not by fossilizing it', async () => {
    const { library, mem } = makeLocalLibrary(seed({ pinnedAt: NOW }));
    const { result } = renderLib(library);
    await waitFor(() => expect(result.current.ready).toBe(true));

    await act(async () => {
      await result.current.pinConversation(ID, false);
    });

    expect(mem.get(ID) && 'pinnedAt' in mem.get(ID)!).toBe(false);
  });
});
