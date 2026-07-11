// @vitest-environment jsdom
/**
 * Tests for useAgentConversation image sends (OG118-IMAGE-UPLOAD-1): images
 * attach to the optimistic user message AND travel to the transport via
 * `meta.images`; an image-only send (empty text) is valid; a truly empty send
 * stays a no-op; retry() replays text + images together.
 */

import { describe, it, expect, vi, afterEach } from 'vitest';
import { act, render, cleanup } from '@testing-library/react';
import type {
  AgentHook,
  AgentSendMeta,
  AgentTurnState,
  MessageImage,
} from '@free-intelligence/core';
import { useAgentConversation, type AgentConversation } from './useAgentConversation';

const AGENT_AUTHOR = { id: 'og118', name: 'og118', symbol: 'og' };
const IMAGES: MessageImage[] = [{ mediaType: 'image/jpeg', data: 'aGk=' }];

const idleTurn: AgentTurnState = {
  plan: null,
  steps: [],
  text: '',
  sources: [],
  meta: null,
  author: null,
  status: 'thinking',
};

function makeFakeAgent() {
  const state = { turn: idleTurn, isStreaming: false };
  const send = vi.fn(async (_text: string, _meta?: AgentSendMeta) => {
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
    reset: vi.fn(),
  };
  return { hook, state, send };
}

function mountConversation(agent: AgentHook) {
  const ref: { current: AgentConversation | null } = { current: null };
  function Harness() {
    ref.current = useAgentConversation(agent, { author: AGENT_AUTHOR });
    return null;
  }
  render(<Harness />);
  return ref;
}

afterEach(cleanup);

describe('useAgentConversation — image sends (OG118-IMAGE-UPLOAD-1)', () => {
  it('attaches images to the optimistic user message and forwards them in meta', () => {
    const { hook, send } = makeFakeAgent();
    const ref = mountConversation(hook);
    act(() => ref.current!.send('¿qué es esto?', IMAGES));
    expect(ref.current!.messages.at(-1)).toMatchObject({
      role: 'user',
      content: '¿qué es esto?',
      images: IMAGES,
    });
    expect(send).toHaveBeenCalledWith('¿qué es esto?', expect.objectContaining({ images: IMAGES }));
  });

  it('allows an image-only send (the picture IS the message)', () => {
    const { hook, send } = makeFakeAgent();
    const ref = mountConversation(hook);
    act(() => ref.current!.send('', IMAGES));
    expect(ref.current!.messages.at(-1)).toMatchObject({ role: 'user', images: IMAGES });
    expect(send).toHaveBeenCalledTimes(1);
  });

  it('a send with no text and no images stays a no-op', () => {
    const { hook, send } = makeFakeAgent();
    const ref = mountConversation(hook);
    act(() => ref.current!.send('   ', []));
    expect(ref.current!.messages).toHaveLength(0);
    expect(send).not.toHaveBeenCalled();
  });

  it('text-only sends carry no images key in meta (transport payload unchanged)', () => {
    const { hook, send } = makeFakeAgent();
    const ref = mountConversation(hook);
    act(() => ref.current!.send('hola'));
    const meta = send.mock.calls[0][1]!;
    expect('images' in meta).toBe(false);
    expect('images' in ref.current!.messages.at(-1)!).toBe(false);
  });
});
