/**
 * OG118-EXTERNAL-TURN-1 — a turn the engine released WITHOUT its answer shows a
 * waiting notice: status, not alert, and nothing to retry. Static SSR markup is
 * enough: the banner either renders with the right role and copy or it does not.
 */

import { describe, it, expect } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import type { ChatMessage } from '@free-intelligence/core';
import { AgentConversationSurface } from './AgentConversationSurface';
import type { AgentConversation } from './useAgentConversation';

const idleTurn = {
  plan: null,
  steps: [],
  text: '',
  sources: [],
  reactions: [],
  meta: null,
  author: null,
  heartbeats: 0,
  deferred: false,
  status: 'done',
} as unknown as AgentConversation['turn'];

const messages: ChatMessage[] = [
  { role: 'user', content: 'un mensaje largo', timestamp: '2026-10-15T19:43:06Z' },
];

const NOTICE = 'Yodo sigue escribiendo. Su respuesta aparecerá aquí en cuanto termine.';

const conversation = (notice: boolean): AgentConversation =>
  ({
    messages,
    turn: idleTurn,
    author: { id: 'og118', name: 'og118', symbol: 'og' },
    isStreaming: false,
    turnError: null,
    turnNotice: notice ? { kind: 'deferred', message: NOTICE } : null,
    dismissNotice: () => {},
    canSend: true,
    send: () => true,
    sendAndAwait: () => Promise.resolve(''),
    retry: () => {},
    dismissError: () => {},
    persistError: null,
    unsentText: null,
    unsentImages: null,
    clearUnsent: () => {},
    retryPersist: () => {},
    dismissPersistError: () => {},
    newConversation: () => {},
  }) as AgentConversation;

describe('<AgentConversationSurface> deferred-turn notice', () => {
  it('renders the notice as a status with the speaker and no retry button', () => {
    const html = renderToStaticMarkup(<AgentConversationSurface conversation={conversation(true)} />);
    expect(html).toContain('role="status"');
    expect(html).toContain(NOTICE);
    expect(html).toContain('Descartar');
    expect(html).not.toContain('Reintentar');
    expect(html).not.toContain('role="alert"');
  });

  it('renders nothing extra when there is no notice', () => {
    const html = renderToStaticMarkup(<AgentConversationSurface conversation={conversation(false)} />);
    expect(html).not.toContain('role="status"');
    expect(html).not.toContain('sigue escribiendo');
  });
});
