// @vitest-environment jsdom
/**
 * useConversationLibrary — rename behavior (B3-FIGLASS-CONVERSATION-RENAME-1).
 *
 * Pins the framework guarantee behind editable chat names: a user rename sticks
 * in the sidebar list AND survives the next message persist (the title is not
 * re-derived once it is custom). Empty rename reverts to the auto-derived title.
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

function makeFakeLibrary(): ConversationLibrary {
  const mem = new Map<string, ConversationRecord>();
  return {
    list: vi.fn(
      async (): Promise<ConversationSummary[]> =>
        [...mem.values()]
          .map(summarizeConversation)
          .sort((a, b) => b.updatedAt.localeCompare(a.updatedAt)),
    ),
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
}

const ID = 'conv-1';
function msg(content: string): ChatMessage {
  return { role: 'user', content, timestamp: '2026-06-24T00:00:00.000Z' };
}

function renderLib(library: ConversationLibrary) {
  return renderHook(() =>
    useConversationLibrary(library, {
      idFactory: () => ID,
      now: () => '2026-06-24T00:00:00.000Z',
    }),
  );
}

describe('useConversationLibrary — renameConversation', () => {
  it('renames a conversation in the sidebar list', async () => {
    const lib = makeFakeLibrary();
    const { result } = renderLib(lib);
    await waitFor(() => expect(result.current.ready).toBe(true));

    await act(async () => {
      await result.current.persist([msg('what is the capital of mexico')]);
    });
    expect(result.current.conversations[0].title).toBe(
      'what is the capital of mexico',
    );

    await act(async () => {
      await result.current.renameConversation(ID, 'Geography qs');
    });
    expect(result.current.conversations[0].title).toBe('Geography qs');
    expect(result.current.activeRecord?.titleCustom).toBe(true);
  });

  it('keeps the custom title when more messages are persisted', async () => {
    const lib = makeFakeLibrary();
    const { result } = renderLib(lib);
    await waitFor(() => expect(result.current.ready).toBe(true));

    await act(async () => {
      await result.current.persist([msg('first message')]);
    });
    await act(async () => {
      await result.current.renameConversation(ID, 'Pinned Name');
    });
    // A new turn persists — the title must NOT re-derive to "first message".
    await act(async () => {
      await result.current.persist([msg('first message'), msg('second')]);
    });
    expect(result.current.activeRecord?.title).toBe('Pinned Name');
    expect(result.current.conversations[0].title).toBe('Pinned Name');
  });

  it('reverts to the derived title on an empty rename', async () => {
    const lib = makeFakeLibrary();
    const { result } = renderLib(lib);
    await waitFor(() => expect(result.current.ready).toBe(true));

    await act(async () => {
      await result.current.persist([msg('derive me')]);
    });
    await act(async () => {
      await result.current.renameConversation(ID, 'Custom');
    });
    await act(async () => {
      await result.current.renameConversation(ID, '   ');
    });
    expect(result.current.activeRecord?.title).toBe('derive me');
    expect(result.current.activeRecord?.titleCustom).toBe(false);
  });

  it('throws clearly when renaming a missing conversation', async () => {
    const lib = makeFakeLibrary();
    const { result } = renderLib(lib);
    await waitFor(() => expect(result.current.ready).toBe(true));

    await expect(
      result.current.renameConversation('ghost', 'x'),
    ).rejects.toThrow(/not found/);
  });
});

describe('useConversationLibrary — pin & archive (CONV-ORGANIZE-1)', () => {
  it('pins a conversation and the flag survives the next message persist', async () => {
    const lib = makeFakeLibrary();
    const { result } = renderLib(lib);
    await waitFor(() => expect(result.current.ready).toBe(true));

    await act(async () => {
      await result.current.persist([msg('first')]);
    });
    await act(async () => {
      await result.current.pinConversation(ID, true);
    });
    expect(result.current.conversations[0].pinnedAt).toBe(
      '2026-06-24T00:00:00.000Z',
    );
    // A new turn persists — organization flags must NOT be silently dropped.
    await act(async () => {
      await result.current.persist([msg('first'), msg('second')]);
    });
    expect(result.current.conversations[0].pinnedAt).toBe(
      '2026-06-24T00:00:00.000Z',
    );

    await act(async () => {
      await result.current.pinConversation(ID, false);
    });
    expect('pinnedAt' in result.current.conversations[0]).toBe(false);
  });

  it('archives (clearing any pin) and unarchives', async () => {
    const lib = makeFakeLibrary();
    const { result } = renderLib(lib);
    await waitFor(() => expect(result.current.ready).toBe(true));

    await act(async () => {
      await result.current.persist([msg('hola')]);
    });
    await act(async () => {
      await result.current.pinConversation(ID, true);
    });
    await act(async () => {
      await result.current.archiveConversation(ID, true);
    });
    const archived = result.current.conversations[0];
    expect(archived.archivedAt).toBe('2026-06-24T00:00:00.000Z');
    expect('pinnedAt' in archived).toBe(false);

    await act(async () => {
      await result.current.archiveConversation(ID, false);
    });
    expect('archivedAt' in result.current.conversations[0]).toBe(false);
  });

  it('throws clearly when pinning a missing conversation', async () => {
    const lib = makeFakeLibrary();
    const { result } = renderLib(lib);
    await waitFor(() => expect(result.current.ready).toBe(true));

    await expect(result.current.pinConversation('ghost', true)).rejects.toThrow(
      /not found/,
    );
  });
});
