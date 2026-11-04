// @vitest-environment jsdom
/**
 * useAgentConversation — seedVersion (OG118-BACKGROUND-1).
 *
 * The same conversationId can gain messages from another writer. A bumped
 * `seedVersion` re-seeds the thread from `initialMessages` — silently (no
 * persist echo), never mid-turn, and without resetting the live turn the way
 * an identity switch does.
 */

import { describe, it, expect, vi, afterEach } from 'vitest';
import { act, cleanup, renderHook } from '@testing-library/react';
import type { AgentHook, AgentTurnState, ChatMessage } from '@free-intelligence/core';
import { useAgentConversation } from './useAgentConversation';

const AUTHOR = { id: 'og118', name: 'og118', symbol: 'og' };
const T0 = '2026-09-12T00:00:00.000Z';
const T1 = '2026-09-12T00:05:00.000Z';

const thinkingTurn: AgentTurnState = {
  plan: null,
  steps: [],
  text: '',
  sources: [],
  meta: null,
  author: null,
  heartbeats: 0,
  deferred: false,
  reactions: [],
  status: 'thinking',
};

function makeFakeAgent() {
  const state = { turn: thinkingTurn, isStreaming: false };
  const reset = vi.fn();
  const send = vi.fn(async () => {
    state.turn = { ...thinkingTurn };
    state.isStreaming = true;
  });
  const hook: AgentHook = {
    get turn() {
      return state.turn;
    },
    get isStreaming() {
      return state.isStreaming;
    },
    send,
    abort: vi.fn(),
    reset,
  };
  return { hook, state, reset };
}

function m(role: ChatMessage['role'], content: string, timestamp = T0): ChatMessage {
  return { role, content, timestamp, author: AUTHOR };
}

interface Props {
  conversationId: string;
  initialMessages: ChatMessage[];
  seedVersion: string;
}

function mount(agent: AgentHook, initial: Props, onMessagesChange = vi.fn()) {
  const utils = renderHook(
    (p: Props) =>
      useAgentConversation(agent, {
        author: AUTHOR,
        turnTimeoutMs: 0,
        onMessagesChange,
        ...p,
      }),
    { initialProps: initial },
  );
  return { ...utils, onMessagesChange };
}

const seed0 = [m('user', 'hola')];
const seed1 = [m('user', 'hola'), m('assistant', 'reporte listo', T1)];

describe('useAgentConversation — seedVersion', () => {
  afterEach(cleanup);

  it('a bumped seedVersion re-hydrates from initialMessages WITHOUT firing onMessagesChange', async () => {
    const { hook, reset } = makeFakeAgent();
    const { result, rerender, onMessagesChange } = mount(hook, {
      conversationId: 'c1',
      initialMessages: seed0,
      seedVersion: T0,
    });
    expect(result.current.messages).toHaveLength(1);

    await act(async () => {
      rerender({ conversationId: 'c1', initialMessages: seed1, seedVersion: T1 });
    });
    expect(result.current.messages).toHaveLength(2);
    expect(result.current.messages[1].content).toBe('reporte listo');
    expect(onMessagesChange).not.toHaveBeenCalled();
    // Same conversation: the live turn is NOT reset (only an identity switch does that).
    expect(reset).not.toHaveBeenCalled();
  });

  it('a new seed array with the SAME seedVersion does not re-hydrate', async () => {
    const { hook } = makeFakeAgent();
    const { result, rerender } = mount(hook, {
      conversationId: 'c1',
      initialMessages: seed0,
      seedVersion: T0,
    });
    await act(async () => {
      rerender({ conversationId: 'c1', initialMessages: [...seed1], seedVersion: T0 });
    });
    expect(result.current.messages).toHaveLength(1);
  });

  it('merges the re-seed while a turn is streaming (optimistic message stays, nothing persisted yet)', async () => {
    const { hook, state } = makeFakeAgent();
    const { result, rerender, onMessagesChange } = mount(hook, {
      conversationId: 'c1',
      initialMessages: seed0,
      seedVersion: T0,
    });
    await act(async () => {
      await result.current.send('¿ya está?');
    });
    // Re-render so the hook observes the streaming transport.
    await act(async () => {
      rerender({ conversationId: 'c1', initialMessages: seed0, seedVersion: T0 });
    });
    expect(state.isStreaming).toBe(true);
    expect(result.current.messages.map((x) => x.content)).toEqual(['hola', '¿ya está?']);

    await act(async () => {
      rerender({ conversationId: 'c1', initialMessages: seed1, seedVersion: T1 });
    });
    expect(result.current.messages.map((x) => x.content)).toEqual(['hola', 'reporte listo', '¿ya está?']);
    expect(onMessagesChange).not.toHaveBeenCalled();
  });

  it('a server append that lands mid-turn survives the fold and is saved with it', async () => {
    const { hook, state } = makeFakeAgent();
    const { result, rerender, onMessagesChange } = mount(hook, {
      conversationId: 'c1',
      initialMessages: seed0,
      seedVersion: T0,
    });
    await act(async () => {
      await result.current.send('¿ya está?');
    });
    await act(async () => {
      rerender({ conversationId: 'c1', initialMessages: seed0, seedVersion: T0 });
    });
    await act(async () => {
      rerender({ conversationId: 'c1', initialMessages: seed1, seedVersion: T1 });
    });
    state.turn = { ...thinkingTurn, text: 'casi', status: 'done' };
    state.isStreaming = false;
    await act(async () => {
      rerender({ conversationId: 'c1', initialMessages: seed1, seedVersion: T1 });
    });
    const thread = ['hola', 'reporte listo', '¿ya está?', 'casi'];
    expect(result.current.messages.map((x) => x.content)).toEqual(thread);
    const saved = onMessagesChange.mock.calls.at(-1)?.[0] as ChatMessage[];
    expect(saved.map((x) => x.content)).toEqual(thread);
  });

  it('the consumer’s own persist echo (same thread, new version) is a no-op', async () => {
    const { hook } = makeFakeAgent();
    const { result, rerender } = mount(hook, {
      conversationId: 'c1',
      initialMessages: seed1,
      seedVersion: T0,
    });
    const before = result.current.messages;
    await act(async () => {
      rerender({ conversationId: 'c1', initialMessages: seed1.map((x) => ({ ...x })), seedVersion: T1 });
    });
    expect(result.current.messages).toBe(before);
  });

  it('an identity switch still re-hydrates and resets the live turn', async () => {
    const { hook, reset } = makeFakeAgent();
    const { result, rerender } = mount(hook, {
      conversationId: 'c1',
      initialMessages: seed0,
      seedVersion: T0,
    });
    await act(async () => {
      rerender({ conversationId: 'c2', initialMessages: seed1, seedVersion: T0 });
    });
    expect(result.current.messages).toHaveLength(2);
    expect(reset).toHaveBeenCalledTimes(1);
  });
});
