// @vitest-environment jsdom
/**
 * A turn belongs to the conversation it was sent in.
 *
 * og118 opens on the local store while the cloud one wakes up (~21 s cold
 * start, composer enabled), then swaps to the remote store. That swap used to
 * re-run the library hydrate and jump to the cloud's most recent conversation
 * mid-turn: the question vanished, the answer folded into the wrong thread and
 * nothing was saved. These tests compose the two hooks exactly as og118 does.
 */
import { afterEach, describe, expect, it, vi } from 'vitest';
import { act, cleanup, renderHook, waitFor } from '@testing-library/react';
import type {
  AgentHook,
  AgentTurnState,
  ChatMessage,
  ConversationLibrary,
  ConversationRecord,
} from '@free-intelligence/core';
import { useAgentConversation } from '../agent/useAgentConversation';
import { EphemeralConversationLibrary } from './EphemeralConversationLibrary';
import { useConversationLibrary } from './useConversationLibrary';

const AUTHOR = { id: 'og118', name: 'og118', symbol: 'og' };
const T0 = '2026-10-09T10:00:00.000Z';
const T1 = '2026-10-09T11:00:00.000Z';

const idle: AgentTurnState = {
  plan: null,
  steps: [],
  text: '',
  sources: [],
  meta: null,
  author: null,
  heartbeats: 0,
  reactions: [],
  status: 'thinking',
};

function fakeAgent() {
  const state = { turn: idle, isStreaming: false };
  const hook: AgentHook = {
    get turn() {
      return state.turn;
    },
    get isStreaming() {
      return state.isStreaming;
    },
    send: vi.fn(async () => {
      state.turn = { ...idle };
      state.isStreaming = true;
    }),
    abort: vi.fn(() => {
      state.isStreaming = false;
    }),
    reset: vi.fn(() => {
      state.turn = idle;
    }),
  };
  const settle = (text: string) => {
    state.turn = { ...idle, text, status: 'done' };
    state.isStreaming = false;
  };
  return { hook, state, settle };
}

function msg(role: ChatMessage['role'], content: string, timestamp = T0): ChatMessage {
  return { role, content, timestamp };
}

function rec(id: string, updatedAt: string, messages: ChatMessage[]): ConversationRecord {
  return {
    id,
    title: id,
    createdAt: T0,
    updatedAt,
    messages,
    preview: messages[messages.length - 1]?.content ?? '',
    schemaVersion: 1,
  };
}

async function store(...records: ConversationRecord[]) {
  const lib = new EphemeralConversationLibrary();
  for (const r of records) await lib.put(r);
  return lib;
}

function mountComposed(agent: AgentHook, initial: ConversationLibrary, idFactory = () => 'fresh') {
  return renderHook(
    ({ library }: { library: ConversationLibrary }) => {
      const lib = useConversationLibrary(library, { idFactory });
      const conversation = useAgentConversation(agent, {
        author: AUTHOR,
        turnTimeoutMs: 0,
        conversationId: lib.activeId,
        initialMessages: lib.activeMessages,
        seedVersion: lib.activeRecord?.updatedAt,
        onMessagesChange: lib.persist,
        onTurnStart: lib.claimActive,
      });
      return { lib, conversation };
    },
    { initialProps: { library: initial } },
  );
}

describe('a turn owns its conversation across a library swap', () => {
  afterEach(cleanup);

  it('swap mid-turn keeps X active and persists question + answer into X', async () => {
    const local = await store(rec('X', T0, [msg('user', 'antes'), msg('assistant', 'ok')]));
    const remote = await store(
      rec('X', T0, [msg('user', 'antes'), msg('assistant', 'ok')]),
      rec('Y', T1, [msg('user', 'otro chat')]),
    );
    const { hook, settle } = fakeAgent();
    const h = mountComposed(hook, local);
    await waitFor(() => expect(h.result.current.lib.activeId).toBe('X'));

    await act(async () => {
      h.result.current.conversation.send('¿sigue ahí?');
    });
    await act(async () => {
      h.rerender({ library: remote });
    });
    await act(async () => {});

    expect(h.result.current.lib.activeId).toBe('X');
    expect(h.result.current.conversation.messages.map((m) => m.content)).toContain('¿sigue ahí?');

    settle('sí');
    await act(async () => {
      h.rerender({ library: remote });
    });

    await waitFor(async () => {
      const saved = await remote.get('X');
      expect(saved?.messages.map((m) => m.content)).toEqual(['antes', 'ok', '¿sigue ahí?', 'sí']);
    });
    expect(h.result.current.lib.activeId).toBe('X');
    expect((await remote.get('Y'))?.messages).toHaveLength(1);
  });

  it('a swap that merges an older cloud copy does not cut the turn in flight', async () => {
    const local = await store(
      rec('X', T1, [msg('user', 'antes'), msg('assistant', 'ok'), msg('user', 'offline', T1), msg('assistant', 'visto', T1)]),
    );
    const remote = await store(rec('X', T0, [msg('user', 'antes'), msg('assistant', 'ok')]));
    const { hook, settle } = fakeAgent();
    const h = mountComposed(hook, local);
    await waitFor(() => expect(h.result.current.lib.activeId).toBe('X'));

    await act(async () => {
      h.result.current.conversation.send('¿sigue ahí?');
    });
    await act(async () => {
      h.rerender({ library: remote });
    });
    await act(async () => {});

    expect(hook.abort).not.toHaveBeenCalled();
    settle('sí');
    await act(async () => {
      h.rerender({ library: remote });
    });
    await waitFor(async () => {
      const saved = await remote.get('X');
      expect(saved?.messages.map((m) => m.content)).toEqual([
        'antes', 'ok', 'offline', 'visto', '¿sigue ahí?', 'sí',
      ]);
    });
  });

  it('a turn started in a never-saved chat is not dragged to the cloud list[0]', async () => {
    const local = await store();
    const remote = await store(rec('Y', T1, [msg('user', 'otro chat')]));
    const { hook, settle } = fakeAgent();
    const h = mountComposed(hook, local);
    await waitFor(() => expect(h.result.current.lib.activeId).toBe('fresh'));

    await act(async () => {
      h.result.current.conversation.send('primera pregunta');
    });
    await act(async () => {
      h.rerender({ library: remote });
    });
    await act(async () => {});
    expect(h.result.current.lib.activeId).toBe('fresh');

    settle('primera respuesta');
    await act(async () => {
      h.rerender({ library: remote });
    });
    await waitFor(async () => {
      const saved = await remote.get('fresh');
      expect(saved?.messages.map((m) => m.content)).toEqual(['primera pregunta', 'primera respuesta']);
    });
  });

  it('an untouched fresh chat still lands on the cloud most-recent after the swap', async () => {
    const local = await store();
    const remote = await store(rec('Y', T1, [msg('user', 'otro chat')]));
    const { hook } = fakeAgent();
    const h = mountComposed(hook, local);
    await waitFor(() => expect(h.result.current.lib.activeId).toBe('fresh'));
    await act(async () => {
      h.rerender({ library: remote });
    });
    await waitFor(() => expect(h.result.current.lib.activeId).toBe('Y'));
  });

  it('sendAndAwait rejects instead of hanging when the conversation switches mid-turn', async () => {
    const lib = await store(
      rec('X', T1, [msg('user', 'x')]),
      rec('Z', T0, [msg('user', 'z')]),
    );
    const { hook } = fakeAgent();
    const h = mountComposed(hook, lib);
    await waitFor(() => expect(h.result.current.lib.activeId).toBe('X'));

    let outcome: unknown = 'pending';
    await act(async () => {
      h.result.current.conversation.sendAndAwait('hola por voz').then(
        () => (outcome = 'resolved'),
        (e: unknown) => (outcome = e),
      );
    });
    await act(async () => {
      await h.result.current.lib.switchConversation('Z');
    });
    await act(async () => {});
    expect(outcome).toBeInstanceOf(Error);
    expect(h.result.current.lib.activeId).toBe('Z');
    await waitFor(async () => {
      const saved = await lib.get('X');
      expect(saved?.messages.map((m) => m.content)).toEqual(['x', 'hola por voz']);
    });
  });
});

describe('persist never drags the user back', () => {
  afterEach(cleanup);

  it('a persist that resolves after the user switched to Z leaves Z active', async () => {
    const backing = await store(
      rec('A', T1, [msg('user', 'a')]),
      rec('Z', T0, [msg('user', 'z')]),
    );
    let releasePut: () => void = () => {};
    const slow: ConversationLibrary = {
      list: () => backing.list(),
      get: (id) => backing.get(id),
      delete: (id) => backing.delete(id),
      clear: () => backing.clear(),
      put: (r) =>
        new Promise<void>((resolve) => {
          releasePut = () => void backing.put(r).then(resolve);
        }),
    };
    const h = renderHook(() => useConversationLibrary(slow));
    await waitFor(() => expect(h.result.current.activeId).toBe('A'));

    let persisting: Promise<void> = Promise.resolve();
    act(() => {
      persisting = h.result.current.persist([msg('user', 'a'), msg('assistant', 'respuesta')], 'A');
    });
    await act(async () => {
      await h.result.current.switchConversation('Z');
    });
    await act(async () => {
      releasePut();
      await persisting;
    });

    expect(h.result.current.activeId).toBe('Z');
    expect(h.result.current.activeMessages.map((m) => m.content)).toEqual(['z']);
    expect((await backing.get('A'))?.messages).toHaveLength(2);
  });
});

describe('a store that cannot be read is visible state', () => {
  afterEach(cleanup);

  it('list() rejecting on mount becomes actionError, not an unhandled rejection', async () => {
    const unhandled = vi.fn();
    process.on('unhandledRejection', unhandled);
    try {
      const broken: ConversationLibrary = {
        list: () => Promise.reject(new Error('500 Internal Server Error')),
        get: async () => null,
        put: async () => {},
        delete: async () => {},
        clear: async () => {},
      };
      const h = renderHook(() => useConversationLibrary(broken, { idFactory: () => 'fresh' }));
      await waitFor(() => expect(h.result.current.ready).toBe(true));
      await act(async () => {
        await new Promise((r) => setTimeout(r, 0));
      });
      expect(h.result.current.actionError).toMatchObject({
        action: 'load',
        message: '500 Internal Server Error',
      });
      expect(h.result.current.activeId).toBe('fresh');
      expect(unhandled).not.toHaveBeenCalled();
    } finally {
      process.off('unhandledRejection', unhandled);
    }
  });
});
