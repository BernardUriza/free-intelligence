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
import type { AgentHook, AgentSendMeta, AgentTurnState, ChatMessage } from '@free-intelligence/core';
import { useAgentConversation, type AgentConversation } from './useAgentConversation';

const AGENT_AUTHOR = { id: 'og118', name: 'og118', symbol: 'og' };

const thinkingTurn: AgentTurnState = {
  plan: null,
  steps: [],
  text: '',
  sources: [],
  meta: null,
  author: null,
  heartbeats: 0,
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
  const send = vi.fn(async (_text: string, _meta?: AgentSendMeta) => {
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
  opts: Partial<Parameters<typeof useAgentConversation>[1]> = {},
) {
  const options = { author: AGENT_AUTHOR, ...opts };
  const ref: { current: AgentConversation | null } = { current: null };
  let bump = () => {};
  function Harness() {
    const conv = useAgentConversation(agent, options);
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

describe('useAgentConversation — sendAndAwait (RESONANCE voice turns)', () => {
  afterEach(cleanup);

  it('resolves with the final assistant text and persists one user + one assistant capsule', async () => {
    const { hook, state } = makeFakeAgent();
    const { ref, rerender } = mountConversation(hook);
    let resolved: string | undefined;
    await act(async () => {
      ref.current!.sendAndAwait('hola').then((t) => { resolved = t; });
      rerender(); // streaming=true, optimistic user capsule pushed
      state.turn = { ...thinkingTurn, text: 'respuesta de voz' };
      state.isStreaming = false;
      rerender(); // fold effect resolves the promise
      await Promise.resolve();
    });
    expect(resolved).toBe('respuesta de voz');
    const msgs = ref.current!.messages;
    expect(msgs.filter((m) => m.role === 'user')).toHaveLength(1);
    expect(msgs.filter((m) => m.role === 'assistant')).toHaveLength(1);
  });

  it('rejects when the turn errors (so Resonance can recover to listening)', async () => {
    const { hook, state } = makeFakeAgent();
    const { ref, rerender } = mountConversation(hook);
    let rejected = false;
    await act(async () => {
      ref.current!.sendAndAwait('hola').catch(() => { rejected = true; });
      rerender();
      state.turn = errorTurn('boom');
      state.isStreaming = false;
      rerender();
      await Promise.resolve();
    });
    expect(rejected).toBe(true);
  });
});

describe('useAgentConversation — user stop (COMPOSER-FOOTER-ZONES-1)', () => {
  afterEach(cleanup);

  it('is undefined when the transport cannot abort — a surface must not offer stop', () => {
    const { hook } = makeFakeAgent();
    const noAbort: AgentHook = { ...hook, abort: undefined };
    const { ref } = mountConversation(noAbort);
    expect(ref.current!.stop).toBeUndefined();
  });

  it('aborts the in-flight turn on the user\'s request', () => {
    const { hook, abort } = makeFakeAgent();
    const { ref, rerender } = mountConversation(hook);
    act(() => { ref.current!.send('hola'); });
    rerender();
    expect(ref.current!.isStreaming).toBe(true);
    act(() => { ref.current!.stop!(); });
    expect(abort).toHaveBeenCalledTimes(1);
  });

  it('is a no-op when nothing is streaming', () => {
    const { hook, abort } = makeFakeAgent();
    const { ref } = mountConversation(hook);
    act(() => { ref.current!.stop!(); });
    expect(abort).not.toHaveBeenCalled();
  });

  // A user stop is NOT a failure: keep the user's message AND the partial answer
  // the assistant already streamed (ChatGPT parity), with no error banner.
  it('folds the partial assistant text and keeps the user message — no turnError', () => {
    const { hook, state } = makeFakeAgent();
    const { ref, rerender } = mountConversation(hook);
    act(() => { ref.current!.send('hola'); });
    rerender();
    state.turn = { ...thinkingTurn, text: 'respuesta a medio escr' };
    rerender();
    act(() => { ref.current!.stop!(); });
    // A real abort drops streaming WITHOUT emitting an error event.
    state.isStreaming = false;
    rerender();

    const msgs = ref.current!.messages;
    expect(msgs.filter((m) => m.role === 'user')).toHaveLength(1);
    expect(msgs.filter((m) => m.role === 'assistant')).toHaveLength(1);
    expect(msgs.find((m) => m.role === 'assistant')!.content).toBe('respuesta a medio escr');
    expect(ref.current!.turnError).toBeNull();
    expect(ref.current!.isStreaming).toBe(false);
  });

  it('keeps the user message alone when stopped before any text streamed', () => {
    const { hook, state } = makeFakeAgent();
    const { ref, rerender } = mountConversation(hook);
    act(() => { ref.current!.send('hola'); });
    rerender();
    act(() => { ref.current!.stop!(); });
    state.isStreaming = false;
    rerender();

    const msgs = ref.current!.messages;
    expect(msgs.filter((m) => m.role === 'user')).toHaveLength(1);
    expect(msgs.filter((m) => m.role === 'assistant')).toHaveLength(0);
    expect(ref.current!.turnError).toBeNull();
  });
});

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

    expect(send).toHaveBeenLastCalledWith('reintenta esto', expect.objectContaining({ history: expect.any(Array) }));
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

/**
 * Mount in CONTROLLED mode with externalMessages owned by the test, plus a
 * setter so a test can update the prop and re-render (the consumer owns the
 * thread). Mirrors mountConversation but threads externalMessages as state.
 */
function mountControlled(
  agent: AgentHook,
  seed: ChatMessage[],
  opts: Partial<Omit<Parameters<typeof useAgentConversation>[1] & object, 'externalMessages'>> = {},
) {
  const ref: { current: AgentConversation | null } = { current: null };
  let setExternal: (m: ChatMessage[]) => void = () => {};
  let bump = () => {};
  function Harness() {
    const [external, setExt] = useState<ChatMessage[]>(seed);
    const [, setN] = useState(0);
    const conv = useAgentConversation(agent, {
      author: AGENT_AUTHOR,
      ...opts,
      externalMessages: external,
    });
    ref.current = conv;
    useEffect(() => {
      setExternal = (m) => setExt(m);
      bump = () => setN((n) => n + 1);
    }, []);
    return null;
  }
  render(<Harness />);
  return {
    ref,
    setExternal: (m: ChatMessage[]) => act(() => setExternal(m)),
    rerender: () => act(() => bump()),
  };
}

const userMsg = (id: string, text: string): ChatMessage => ({
  id,
  role: 'user',
  content: text,
  timestamp: '2026-06-16T00:00:00.000Z',
});

const agentMsg = (id: string, text: string): ChatMessage => ({
  id,
  role: 'assistant',
  content: text,
  timestamp: '2026-06-16T00:00:00.000Z',
});

describe('useAgentConversation — controlled / external-transcript mode (FIGLASS-CONTROLLED)', () => {
  afterEach(cleanup);

  it('returns externalMessages verbatim, not the internal array', () => {
    const { hook } = makeFakeAgent();
    const seed = [userMsg('u1', 'inicia'), agentMsg('a1', 'CAMPAIGN handoff')];
    const { ref } = mountControlled(hook, seed, { turnTimeoutMs: 0 });

    expect(ref.current!.messages).toBe(seed);
  });

  it('updates conversation.messages when the externalMessages prop changes', () => {
    const { hook } = makeFakeAgent();
    const seed = [userMsg('u1', 'inicia')];
    const { ref, setExternal } = mountControlled(hook, seed, { turnTimeoutMs: 0 });

    const next = [
      userMsg('u1', 'inicia'),
      agentMsg('a1', 'CAMPAIGN'),
      agentMsg('a2', 'SAFETY veto'),
      agentMsg('a3', 'CAMPAIGN revise'),
    ];
    setExternal(next);

    expect(ref.current!.messages).toBe(next);
    expect(ref.current!.messages).toHaveLength(4);
  });

  it('send() drives agent.send and does NOT push or fold into the thread', () => {
    const { hook, state, send } = makeFakeAgent();
    const seed = [userMsg('u1', 'previo')];
    const { ref, rerender } = mountControlled(hook, seed, { turnTimeoutMs: 0 });

    act(() => ref.current!.send('arranca el workflow'));
    rerender();
    // Controlled mode still hands the transport the visible thread (externalMessages)
    // as history for storeless continuity.
    expect(send).toHaveBeenCalledWith('arranca el workflow', { history: seed });
    // No optimistic push: the consumer's externalMessages is still the only truth.
    expect(ref.current!.messages).toBe(seed);
    expect(ref.current!.messages).toHaveLength(1);

    // A clean finish does NOT fold an assistant message into the thread either.
    act(() => {
      state.turn = doneTurn('un solo turno colapsado');
      state.isStreaming = false;
    });
    rerender();
    expect(ref.current!.messages).toBe(seed);
    expect(ref.current!.messages).toHaveLength(1);
  });

  it('surfaces turnError on a transport error without crashing on the no-op revert', () => {
    const { hook, state } = makeFakeAgent();
    const seed = [userMsg('u1', 'arranca')];
    const { ref, rerender } = mountControlled(hook, seed, { turnTimeoutMs: 0 });

    act(() => ref.current!.send('workflow que falla'));
    rerender();
    act(() => {
      state.turn = errorTurn('workflow reventó');
      state.isStreaming = false;
    });
    rerender();

    expect(ref.current!.turnError).toEqual({ kind: 'stream', message: 'workflow reventó' });
    // The thread is untouched — revert is a no-op (nothing was optimistically pushed).
    expect(ref.current!.messages).toBe(seed);
    expect(ref.current!.isStreaming).toBe(false);
  });

  it('idle watchdog still recovers a hung controlled turn (timeout error, abort)', () => {
    vi.useFakeTimers();
    const { hook, state, abort } = makeFakeAgent();
    const seed = [userMsg('u1', 'arranca')];
    const { ref, rerender } = mountControlled(hook, seed, { turnTimeoutMs: 1000 });

    act(() => ref.current!.send('workflow que se cuelga'));
    rerender();
    expect(ref.current!.isStreaming).toBe(true);

    act(() => vi.advanceTimersByTime(1000));
    rerender();

    expect(ref.current!.isStreaming).toBe(false);
    expect(state.isStreaming).toBe(true); // transport still stuck
    expect(ref.current!.turnError).toEqual({ kind: 'timeout', message: expect.any(String) });
    expect(abort).toHaveBeenCalledTimes(1);
    expect(ref.current!.messages).toBe(seed); // untouched
    vi.useRealTimers();
  });

  it('never calls onMessagesChange in controlled mode (consumer owns persistence)', () => {
    const onMessagesChange = vi.fn();
    const { hook, state } = makeFakeAgent();
    const seed = [userMsg('u1', 'arranca')];
    const { ref, rerender } = mountControlled(hook, seed, { turnTimeoutMs: 0, onMessagesChange });

    act(() => ref.current!.send('workflow'));
    rerender();
    act(() => {
      state.turn = doneTurn('listo');
      state.isStreaming = false;
    });
    rerender();

    expect(onMessagesChange).not.toHaveBeenCalled();
  });

  it('externalMessages wins over initialMessages when both are passed', () => {
    const { hook } = makeFakeAgent();
    const seed = [agentMsg('a1', 'externo gana')];
    const { ref } = mountControlled(hook, seed, {
      turnTimeoutMs: 0,
      initialMessages: [userMsg('seed', 'esto se ignora')],
    });

    expect(ref.current!.messages).toBe(seed);
  });
});

describe('useAgentConversation — client-supplied history for storeless continuity', () => {
  afterEach(cleanup);

  it('hands the transport the confirmed thread as meta.history, excluding the new message', () => {
    const { hook, send } = makeFakeAgent();
    const seed = [userMsg('u1', '¿chance de México?'), agentMsg('a1', 'limitadas')];
    const { ref } = mountConversation(hook, { turnTimeoutMs: 0, initialMessages: seed });

    act(() => ref.current!.send('han ganado otro!'));

    expect(send).toHaveBeenCalledWith('han ganado otro!', { history: seed });
    const meta = send.mock.calls[0][1] as { history: ChatMessage[] };
    expect(meta.history.some((m) => m.content === 'han ganado otro!')).toBe(false);
  });

  it('sends empty history on the first turn', () => {
    const { hook, send } = makeFakeAgent();
    const { ref } = mountConversation(hook, { turnTimeoutMs: 0 });

    act(() => ref.current!.send('primera'));

    expect(send).toHaveBeenCalledWith('primera', { history: [] });
  });
});

describe('persist failure — a save that fails may NOT fail in silence', () => {
  afterEach(cleanup);

  /** Drive one full turn (send → settled answer) so the fold triggers a persist. */
  async function foldOneTurn(
    ref: { current: AgentConversation | null },
    state: { turn: AgentTurnState; isStreaming: boolean },
    rerender: () => void,
  ) {
    await act(async () => {
      ref.current!.send('hola');
      rerender();
      state.turn = doneTurn('respuesta');
      state.isStreaming = false;
      rerender();
      await Promise.resolve();
    });
    await act(async () => {
      await Promise.resolve();
      rerender();
    });
  }

  it('surfaces a rejected persist as persistError instead of discarding the promise', async () => {
    const { hook, state } = makeFakeAgent();
    const onMessagesChange = vi.fn().mockRejectedValue(new Error('HTTP 413'));
    const { ref, rerender } = mountConversation(hook, { onMessagesChange });

    await foldOneTurn(ref, state, rerender);

    expect(onMessagesChange).toHaveBeenCalled();
    expect(ref.current!.persistError?.message).toBe('HTTP 413');
    // The thread stays on screen: what failed is the WRITE, not the turn.
    expect(ref.current!.messages).toHaveLength(2);
    expect(ref.current!.turnError).toBeNull();
  });

  it('retryPersist re-attempts the FULL thread and clears the error on success', async () => {
    const { hook, state } = makeFakeAgent();
    // A flag, not mockRejectedValueOnce: the hook persists more than once per
    // turn (optimistic user capsule, then the folded turn), so "fail the first
    // call" would let a later one silently clear the error.
    const failing = { yes: true };
    const onMessagesChange = vi.fn(async (_messages: ChatMessage[]) => {
      if (failing.yes) throw new Error('HTTP 413');
    });
    const { ref, rerender } = mountConversation(hook, { onMessagesChange });

    await foldOneTurn(ref, state, rerender);
    expect(ref.current!.persistError?.message).toBe('HTTP 413');

    failing.yes = false;
    await act(async () => {
      ref.current!.retryPersist();
      await Promise.resolve();
      rerender();
    });

    // It retried the whole confirmed thread (user + assistant), not a fragment.
    const lastCall = onMessagesChange.mock.calls[onMessagesChange.mock.calls.length - 1];
    expect(lastCall[0]).toHaveLength(2);
    expect(ref.current!.persistError).toBeNull();
  });

  it('a successful persist leaves no error', async () => {
    const { hook, state } = makeFakeAgent();
    const { ref, rerender } = mountConversation(hook, {
      onMessagesChange: vi.fn().mockResolvedValue(undefined),
    });
    await foldOneTurn(ref, state, rerender);
    expect(ref.current!.persistError).toBeNull();
  });
});

describe('P0 — a slow turn is not a dead turn, and a failed turn does not eat the prompt', () => {
  afterEach(cleanup);

  it('a heartbeat re-arms the watchdog: a quiet-but-alive turn survives past the timeout', () => {
    vi.useFakeTimers();
    const { hook, state, abort } = makeFakeAgent();
    const { ref, rerender } = mountConversation(hook, { turnTimeoutMs: 1000 });

    act(() => ref.current!.send('hola'));
    rerender();

    // 900ms of silence… then the backend says "still here" (a `ping` bumps
    // heartbeats). This is the case that was killing healthy turns: an external
    // element answers in ONE shot after up to 95s and says nothing until then.
    act(() => {
      vi.advanceTimersByTime(900);
      state.turn = { ...state.turn, heartbeats: state.turn.heartbeats + 1 };
    });
    rerender();
    act(() => {
      vi.advanceTimersByTime(900);
    });
    rerender();

    // Past the raw 1000ms budget, but the turn is ALIVE: no timeout, no abort,
    // and the user's message is still in the thread.
    expect(ref.current!.turnError).toBeNull();
    expect(abort).not.toHaveBeenCalled();
    expect(ref.current!.messages).toHaveLength(1);
    vi.useRealTimers();
  });

  it('silence with NO heartbeat still times out (a hung backend is still caught)', () => {
    vi.useFakeTimers();
    const { hook, abort } = makeFakeAgent();
    const { ref, rerender } = mountConversation(hook, { turnTimeoutMs: 1000 });
    act(() => ref.current!.send('hola'));
    rerender();
    act(() => {
      vi.advanceTimersByTime(1000);
    });
    rerender();
    expect(ref.current!.turnError?.kind).toBe('timeout');
    expect(abort).toHaveBeenCalledTimes(1);
    vi.useRealTimers();
  });

  it('a failed turn HANDS BACK what the user wrote (it used to destroy it)', () => {
    vi.useFakeTimers();
    const { hook } = makeFakeAgent();
    const { ref, rerender } = mountConversation(hook, { turnTimeoutMs: 1000 });

    act(() => ref.current!.send('un prompt que me costó escribir'));
    rerender();
    act(() => {
      vi.advanceTimersByTime(1000);
    });
    rerender();

    // Reverted out of the thread, yes — but NOT lost: the shell puts it back in
    // the composer.
    expect(ref.current!.messages).toHaveLength(0);
    expect(ref.current!.unsentText).toBe('un prompt que me costó escribir');
    vi.useRealTimers();
  });

  it('sending again clears the pending recovery', () => {
    vi.useFakeTimers();
    const { hook, state } = makeFakeAgent();
    const { ref, rerender } = mountConversation(hook, { turnTimeoutMs: 1000 });
    act(() => ref.current!.send('primero'));
    rerender();
    act(() => {
      vi.advanceTimersByTime(1000);
    });
    rerender();
    expect(ref.current!.unsentText).toBe('primero');

    state.isStreaming = false;
    act(() => ref.current!.send('segundo'));
    rerender();
    expect(ref.current!.unsentText).toBeNull();
    vi.useRealTimers();
  });

  it('a failed turn hands back the IMAGES too, not just the words', () => {
    vi.useFakeTimers();
    const { hook } = makeFakeAgent();
    const { ref, rerender } = mountConversation(hook, { turnTimeoutMs: 1000 });

    const img = { mediaType: 'image/png', data: 'BASE64PAYLOAD' };
    act(() => ref.current!.send('mira esta gráfica', [img]));
    rerender();
    expect(ref.current!.messages[0]?.images).toHaveLength(1);

    act(() => {
      vi.advanceTimersByTime(1000);
    });
    rerender();

    // Recovery carries the WHOLE message. Handing back only the text let the
    // user re-send a prompt whose picture had silently ceased to exist.
    expect(ref.current!.messages).toHaveLength(0);
    expect(ref.current!.unsentText).toBe('mira esta gráfica');
    expect(ref.current!.unsentImages).toEqual([img]);
    vi.useRealTimers();
  });

  it('clearUnsent drops BOTH channels (a half-cleared recovery re-attaches a ghost)', () => {
    vi.useFakeTimers();
    const { hook } = makeFakeAgent();
    const { ref, rerender } = mountConversation(hook, { turnTimeoutMs: 1000 });
    act(() => ref.current!.send('con foto', [{ mediaType: 'image/png', data: 'AAA' }]));
    rerender();
    act(() => {
      vi.advanceTimersByTime(1000);
    });
    rerender();
    expect(ref.current!.unsentImages).toHaveLength(1);

    act(() => ref.current!.clearUnsent());
    rerender();
    expect(ref.current!.unsentText).toBeNull();
    expect(ref.current!.unsentImages).toBeNull();
    vi.useRealTimers();
  });
});
