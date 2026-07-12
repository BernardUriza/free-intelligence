/**
 * Tests for the surface's image-attachment switch (OG118-IMAGE-UPLOAD-1):
 * `imageAttachments` lights up the attach trigger, and messages that carry
 * `images` render them in their bubble (so the picture survives into the
 * durable transcript). Static SSR markup — no transport, no live turn.
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
  meta: null,
  status: 'complete',
} as unknown as AgentConversation['turn'];

const makeConversation = (msgs: ChatMessage[]): AgentConversation =>
  ({
    messages: msgs,
    turn: idleTurn,
    author: { id: 'og118', name: 'og118', symbol: 'og' },
    isStreaming: false,
    turnError: null,
    send: () => {},
    sendAndAwait: () => Promise.resolve(''),
    retry: () => {},
    dismissError: () => {},
    persistError: null,
    unsentText: null,
    clearUnsentText: () => {},
    retryPersist: () => {},
    dismissPersistError: () => {},
    newConversation: () => {},
  }) as AgentConversation;

describe('<AgentConversationSurface> image attachments (OG118-IMAGE-UPLOAD-1)', () => {
  it('renders the shared "+" only when there is something to add', () => {
    // No capabilities wired → no trigger at all (an empty "+" is worse than none).
    const off = renderToStaticMarkup(
      <AgentConversationSurface conversation={makeConversation([])} />,
    );
    expect(off).not.toContain('data-fi-composer-actions');

    // Images wired → the framework contributes "Adjuntar imagen" as an ACTION,
    // reachable from the one "+" (not a button of its own).
    const on = renderToStaticMarkup(
      <AgentConversationSurface conversation={makeConversation([])} imageAttachments />,
    );
    expect(on).toContain('data-fi-composer-actions');
    expect(on).toContain('data-fi-image-input');
  });

  it('renders a message\'s attached images inside its bubble', () => {
    const html = renderToStaticMarkup(
      <AgentConversationSurface
        conversation={makeConversation([
          {
            role: 'user',
            content: '¿qué es esto?',
            timestamp: '2026-01-01T00:00:00Z',
            images: [{ mediaType: 'image/png', data: 'aGk=' }],
          },
        ])}
      />,
    );
    expect(html).toContain('data-fi-message-images');
    expect(html).toContain('data:image/png;base64,aGk=');
  });

  it('text-only messages render no image container (transcript unchanged)', () => {
    const html = renderToStaticMarkup(
      <AgentConversationSurface
        conversation={makeConversation([
          { role: 'user', content: 'hola', timestamp: '2026-01-01T00:00:00Z' },
        ])}
      />,
    );
    expect(html).not.toContain('data-fi-message-images');
  });
});
