// @vitest-environment jsdom
/**
 * The resource stamp on a conversation (FIGLASS-PROJECTS-PAGE-1, hueco 4).
 *
 * Before this, the corpus binding was sent per REQUEST and stored nowhere: a
 * conversation started inside a project became indistinguishable from any other
 * the moment it was saved, so the project could never list its own chats.
 *
 * The rule under test is BIRTH-ONLY. A conversation keeps the resource it was
 * started in; changing the selection later must not re-file yesterday's history
 * under whatever happens to be active right now. Getting that backwards would
 * silently rewrite history every time someone clicked a different project.
 */
import { describe, expect, it, vi } from 'vitest';
import { act, renderHook, waitFor } from '@testing-library/react';
import type {
  ChatMessage,
  ConversationLibrary,
  ConversationRecord,
  ConversationSummary,
} from '@free-intelligence/core';
import { summarizeConversation } from '@free-intelligence/core';
import { useConversationLibrary } from './useConversationLibrary';

function makeFakeLibrary() {
  const mem = new Map<string, ConversationRecord>();
  const library = {
    list: vi.fn(
      async (): Promise<ConversationSummary[]> =>
        [...mem.values()].map(summarizeConversation),
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
  return { library, mem };
}

const ID = 'conv-1';
const msg = (content: string): ChatMessage => ({
  role: 'user',
  content,
  timestamp: '2026-08-22T00:00:00.000Z',
});

function renderLib(library: ConversationLibrary, projectId?: string) {
  return renderHook(
    ({ pid }: { pid?: string }) =>
      useConversationLibrary(library, {
        idFactory: () => ID,
        now: () => '2026-08-22T00:00:00.000Z',
        projectId: pid,
      }),
    { initialProps: { pid: projectId } },
  );
}

describe('the resource a conversation is born in', () => {
  it('stamps the active resource onto a brand-new conversation', async () => {
    const { library, mem } = makeFakeLibrary();
    const { result } = renderLib(library, 'project-a');
    await waitFor(() => expect(result.current.ready).toBe(true));

    await act(async () => {
      await result.current.persist([msg('hola')]);
    });

    expect(mem.get(ID)?.projectId).toBe('project-a');
  });

  it('omits the field entirely when no resource is active', async () => {
    const { library, mem } = makeFakeLibrary();
    const { result } = renderLib(library);
    await waitFor(() => expect(result.current.ready).toBe(true));

    await act(async () => {
      await result.current.persist([msg('hola')]);
    });

    expect(mem.get(ID)).not.toHaveProperty('projectId');
  });

  it('does NOT re-file an existing conversation when the selection changes', async () => {
    const { library, mem } = makeFakeLibrary();
    const { result, rerender } = renderLib(library, 'project-a');
    await waitFor(() => expect(result.current.ready).toBe(true));
    await act(async () => {
      await result.current.persist([msg('hola')]);
    });

    rerender({ pid: 'project-b' });
    await act(async () => {
      await result.current.persist([msg('hola'), msg('otra')]);
    });

    expect(mem.get(ID)?.projectId).toBe('project-a');
  });

  it('does not retroactively adopt a resource for a conversation born without one', async () => {
    const { library, mem } = makeFakeLibrary();
    const { result, rerender } = renderLib(library);
    await waitFor(() => expect(result.current.ready).toBe(true));
    await act(async () => {
      await result.current.persist([msg('hola')]);
    });

    rerender({ pid: 'project-b' });
    await act(async () => {
      await result.current.persist([msg('hola'), msg('otra')]);
    });

    expect(mem.get(ID)).not.toHaveProperty('projectId');
  });

  it('rides the SUMMARY, so a per-resource list can filter light rows', async () => {
    const { library } = makeFakeLibrary();
    const { result } = renderLib(library, 'project-a');
    await waitFor(() => expect(result.current.ready).toBe(true));

    await act(async () => {
      await result.current.persist([msg('hola')]);
    });

    await waitFor(() =>
      expect(result.current.conversations[0]?.projectId).toBe('project-a'),
    );
  });
});
