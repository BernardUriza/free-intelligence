/**
 * Tests for AgentConversationSurface per-role bubble styling (B3-VOICE-FIGLASS-3).
 *
 * The tri-consumer visual audit found the only real reusable gap was that this
 * surface could not vary message-bubble styling by role. These tests pin the
 * additive, backward-compatible contract of `messageBubbleClassName`:
 *  - a string still applies to EVERY bubble (legacy behavior, unchanged),
 *  - a function resolver applies DISTINCT classes per role,
 *  - omitting it keeps defaults (no extra bubble class injected),
 *  - a resolver that returns undefined (e.g. an unknown role) never throws.
 *
 * Static SSR markup is enough: we assert the resolved class lands on the
 * rendered bubble — no jsdom, no transport, no live turn.
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

const messages: ChatMessage[] = [
  { role: 'user', content: 'pregunta del usuario', timestamp: '2026-01-01T00:00:00Z' },
  { role: 'assistant', content: 'respuesta del asistente', timestamp: '2026-01-01T00:00:01Z' },
];

const makeConversation = (msgs: ChatMessage[] = messages): AgentConversation =>
  ({
    messages: msgs,
    turn: idleTurn,
    isStreaming: false,
    send: () => {},
    newConversation: () => {},
  }) as AgentConversation;

describe('<AgentConversationSurface> messageBubbleClassName', () => {
  it('applies a string class to every bubble (legacy, unchanged)', () => {
    const html = renderToStaticMarkup(
      <AgentConversationSurface
        conversation={makeConversation()}
        messageBubbleClassName="legacy-bubble"
      />
    );
    // One occurrence per message bubble (user + assistant).
    const occurrences = html.split('legacy-bubble').length - 1;
    expect(occurrences).toBe(2);
  });

  it('applies DISTINCT classes per role via a function resolver', () => {
    const html = renderToStaticMarkup(
      <AgentConversationSurface
        conversation={makeConversation()}
        messageBubbleClassName={(m) =>
          m.role === 'user' ? 'bubble-user' : 'bubble-assistant'
        }
      />
    );
    expect(html).toContain('bubble-user');
    expect(html).toContain('bubble-assistant');
    // The user bubble must NOT get the assistant class and vice versa: assert
    // each custom class appears exactly once.
    expect(html.split('bubble-user').length - 1).toBe(1);
    expect(html.split('bubble-assistant').length - 1).toBe(1);
  });

  it('keeps defaults when omitted (no extra bubble class injected)', () => {
    const html = renderToStaticMarkup(
      <AgentConversationSurface conversation={makeConversation()} />
    );
    // The bubbles still render their content...
    expect(html).toContain('pregunta del usuario');
    expect(html).toContain('respuesta del asistente');
    // ...and no stray "undefined" leaks into a class attribute.
    expect(html).not.toContain('undefined');
  });

  it('does not throw when the resolver returns undefined (unknown role)', () => {
    const withUnknown: ChatMessage[] = [
      ...messages,
      // A role outside the known union — the resolver below ignores it.
      { role: 'system', content: 'nota de sistema', timestamp: '2026-01-01T00:00:02Z' } as unknown as ChatMessage,
    ];
    const render = () =>
      renderToStaticMarkup(
        <AgentConversationSurface
          conversation={makeConversation(withUnknown)}
          messageBubbleClassName={(m) =>
            m.role === 'user' ? 'bubble-user' : undefined
          }
        />
      );
    expect(render).not.toThrow();
    const html = render();
    expect(html).toContain('nota de sistema');
    expect(html).not.toContain('undefined');
  });
});

describe('<AgentConversationSurface> voiceAdapter dictation (B3-VOICE-FIGLASS-4)', () => {
  const synthesizeOnly = {
    defaultVoice: 'nova',
    availableVoices: [],
    synthesize: async () => new Blob(),
  };
  const withTranscribe = {
    ...synthesizeOnly,
    transcribe: async () => ({ text: '' }),
  };

  it('renders no dictation mic when no voiceAdapter is passed (backward-compatible)', () => {
    const html = renderToStaticMarkup(
      <AgentConversationSurface conversation={makeConversation()} />
    );
    // The ComposerMicSlot is the only thing that carries data-available; absent
    // when no adapter → no mic in the composer at all.
    expect(html).not.toContain('data-available');
  });

  it('renders no mic when the adapter lacks a transcribe capability', () => {
    const html = renderToStaticMarkup(
      <AgentConversationSurface
        conversation={makeConversation()}
        voiceAdapter={synthesizeOnly}
      />
    );
    // synthesize-only adapter → STT not available → mic is capability-gated out.
    expect(html).not.toContain('data-available');
  });

  it('lights up an available dictation mic when the adapter can transcribe', () => {
    const html = renderToStaticMarkup(
      <AgentConversationSurface
        conversation={makeConversation()}
        voiceAdapter={withTranscribe}
        micSlotClassName="og-mic-slot"
      />
    );
    // transcribe present → the in-composer mic renders, enabled, and the
    // consumer's style hook lands on it.
    expect(html).toContain('data-available');
    expect(html).toContain('og-mic-slot');
  });

  it('does not throw when rendering an empty thread with dictation enabled', () => {
    const render = () =>
      renderToStaticMarkup(
        <AgentConversationSurface
          conversation={{ ...makeConversation([]), turn: { ...idleTurn, status: 'thinking' } as AgentConversation['turn'] }}
          voiceAdapter={withTranscribe}
          emptyState={<div>start</div>}
        />
      );
    expect(render).not.toThrow();
  });
});
