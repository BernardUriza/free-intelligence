// @vitest-environment jsdom
/**
 * Tests for useAgentConversation turn-failure recovery + persistence contract
 * (B3-FIGLASS-8). The staging daily-driver audit found a hung stream left the UI
 * in "thinking…" forever AND persisted the optimistic user message as durable
 * conversation truth. These tests pin the recovery contract WITHOUT any real
 * transport/provider: a fake AgentHook drives the lifecycle by hand.
 *
 * Covered:
 *  - stream that never resolves → after the idle watchdog, isStreaming drops and
 *    a recoverable timeout error appears;
 *  - transport error status → recoverable stream error, optimistic msg reverted;
 *  - retry() re-sends the same text;
 *  - a failed/hung optimistic message is NEVER persisted (confirmed-only);
 *  - a clean finish persists user + assistant together.
 */

import { describe, it, expect, vi, afterEach } from 'vitest';
import { act, render, cleanup } from '@testing-library/react';
import { useEffect, useState } from 'react';
import type { AgentHook, AgentTurnState } from '@free-intelligence/core';
import { useAgentConversation, type AgentConversation } from './useAgentConversation';

const thinkingTurn: AgentTurnState = {
  plan: null,
  steps: [],
  text: '',
  sources: [],
  meta: null,
  status: 'thinking',
};

const doneTurn = (text: string): AgentTurnState => ({
  ...thinkingTurn,
  text,
  status: 'done',
});

const errorTurn = (message: string): AgentTurnState => ({
  ...thinkingTurn,
  status: 'error',
  errorMessage: message,
});

/**
 * A controllable fake transport. `set()` mutates the turn/streaming the way a
 * real hook would on wire events; the harness re-renders so the conversation's
 * effects observe the change.
 */
function makeFakeAgent() {
  const state = { turn: thinkingTurn, isStreaming: false };
  const abort = vi.fn();
  const reset = vi.fn(() => {
    state.turn = thinkingTurn;
    state.isStreaming = false;
  });
  const send = vi.fn(async () => {
    // A real send flips streaming on and seeds a thinking turn.
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
    abort,
    reset,
  };
  return { hook, state, abort, reset, send };
}

/** Mount the hook and expose the latest conversation + a re-render trigger. */
function mountConversation(
  agent: AgentHook,
  opts: Parameters<typeof useAgentConversation>[1] = {},
) {
  const ref: { current: AgentConversation | null } = { current: null };
  let bump = () => {};
  function Harness() {
    const conv = useAgentConversation(agent, opts);
    ref.current = conv;
    const [, setN] = useState(0);
    useEffect(() => {
      bump = () => setN((n) => n + 1);
    }, []);
    return null;
  }
  const utils = render(<Harness />);
  return { ref, rerender: () => act(() => bump()), utils };
}

describe('useAgentConversation — turn failure recovery (B3-FIGLASS-8)', () => {
  afterEach(cleanup);

  it('drops streaming and surfaces a timeout error when the stream never resolves', () => {
    vi.useFakeTimers();
    const { hook, state, abort } = makeFakeAgent();
    const { ref, rerender } = mountConversation(hook, { turnTimeoutMs: 1000 });

    act(() => ref.current!.send('hola'));
    rerender(); // observe streaming=true after send
    expect(ref.current!.isStreaming).toBe(true);
    expect(ref.current!.messages).toHaveLength(1); // optimistic user msg visible

    // Stream never resolves: isStreaming stays stuck true on the transport.
    act(() => {
      vi.advanceTimersByTime(1000);
    });
    rerender();

    // Watchdog fired: conversation no longer reports streaming, error is set,
    // the transport was aborted, and the optimistic message was reverted.
    expect(ref.current!.isStreaming).toBe(false);
    expect(state.isStreaming).toBe(true); // transport still stuck — we overrode it
    expect(ref.current!.turnError).toEqual({
      kind: 'timeout',
      message: expect.any(String),
    });
    expect(abort).toHaveBeenCalledTimes(1);
    expect(ref.current!.messages).toHaveLength(0);
    vi.useRealTimers();
  });

  it('an active turn keeps re-arming the watchdog and does NOT time out', () => {
    vi.useFakeTimers();
    const { hook, state } = makeFakeAgent();
    const { ref, rerender } = mountConversation(hook, { turnTimeoutMs: 1000 });

    act(() => ref.current!.send('hola'));
    rerender();

    // Token arrives at 800ms — resets the idle watchdog.
    act(() => vi.advanceTimersByTime(800));
    act(() => {
      state.turn = { ...thinkingTurn, text: 'escribiendo', status: 'streaming' };
    });
    rerender();
    act(() => vi.advanceTimersByTime(800)); // 1600ms total, but only 800 since activity

    expect(ref.current!.turnError).toBeNull();
    expect(ref.current!.isStreaming).toBe(true);
    vi.useRealTimers();
  });

  it('surfaces a recoverable stream error and reverts the optimistic message on transport error', () => {
    const { hook, state } = makeFakeAgent();
    const { ref, rerender } = mountConversation(hook, { turnTimeoutMs: 0 });

    act(() => ref.current!.send('pregunta'));
    rerender();
    expect(ref.current!.messages).toHaveLength(1);

    // Transport settles into an error and stops streaming.
    act(() => {
      state.turn = errorTurn('401 no autorizado');
      state.isStreaming = false;
    });
    rerender();

    expect(ref.current!.turnError).toEqual({ kind: 'stream', message: '401 no autorizado' });
    expect(ref.current!.messages).toHaveLength(0); // optimistic reverted, not dropped silently
    expect(ref.current!.isStreaming).toBe(false);
  });

  it('retry() re-sends the same text after a failure', () => {
    const { hook, state, send } = makeFakeAgent();
    const { ref, rerender } = mountConversation(hook, { turnTimeoutMs: 0 });

    act(() => ref.current!.send('reintenta esto'));
    rerender();
    act(() => {
      state.turn = errorTurn('boom');
      state.isStreaming = false;
    });
    rerender();
    expect(ref.current!.turnError).not.toBeNull();

    act(() => ref.current!.retry());
    rerender();

    expect(send).toHaveBeenLastCalledWith('reintenta esto');
    expect(ref.current!.turnError).toBeNull();
    expect(ref.current!.messages).toHaveLength(1); // optimistic re-pushed
  });

  it('never persists a failed/hung optimistic message (confirmed-only persistence)', () => {
    vi.useFakeTimers();
    const onMessagesChange = vi.fn();
    const { hook } = makeFakeAgent();
    const { ref, rerender } = mountConversation(hook, {
      turnTimeoutMs: 1000,
      onMessagesChange,
    });

    act(() => ref.current!.send('se va a colgar'));
    rerender();
    // The optimistic push must NOT have persisted.
    expect(onMessagesChange).not.toHaveBeenCalled();

    act(() => vi.advanceTimersByTime(1000));
    rerender();

    // After the failure, no persisted state ever contained the lone user message.
    for (const call of onMessagesChange.mock.calls) {
      const msgs = call[0] as { role: string }[];
      expect(msgs.some((m) => m.role === 'user')).toBe(false);
    }
    vi.useRealTimers();
  });

  it('does NOT raise a generic error for an app-handled error class (but still reverts)', () => {
    const { hook, state } = makeFakeAgent();
    const { ref, rerender } = mountConversation(hook, {
      turnTimeoutMs: 0,
      // og118-style: claim the 401 token-gate error as app-handled.
      isAppHandledError: (t) => (t.errorMessage ?? '').startsWith('AUTH401'),
    });

    act(() => ref.current!.send('pregunta con token vencido'));
    rerender();
    act(() => {
      state.turn = errorTurn('AUTH401: token inválido');
      state.isStreaming = false;
    });
    rerender();

    // The app handles its own 401 banner: no generic turnError, but the
    // optimistic message is still reverted (never persisted as a lone turn).
    expect(ref.current!.turnError).toBeNull();
    expect(ref.current!.messages).toHaveLength(0);
  });

  it('persists user + assistant together on a clean finish', () => {
    const onMessagesChange = vi.fn();
    const { hook, state } = makeFakeAgent();
    const { ref, rerender } = mountConversation(hook, {
      turnTimeoutMs: 0,
      onMessagesChange,
    });

    act(() => ref.current!.send('pregunta buena'));
    rerender();
    act(() => {
      state.turn = doneTurn('respuesta buena');
      state.isStreaming = false;
    });
    rerender();

    expect(ref.current!.messages).toHaveLength(2);
    expect(ref.current!.turnError).toBeNull();
    const calls = onMessagesChange.mock.calls;
    const lastPersist = calls[calls.length - 1]?.[0] as { role: string }[];
    expect(lastPersist.map((m) => m.role)).toEqual(['user', 'assistant']);
  });
});
