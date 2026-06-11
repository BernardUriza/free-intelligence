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
    turnError: null,
    send: () => {},
    retry: () => {},
    dismissError: () => {},
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

  // B3-VOICE-FIGLASS-5: the live mic equalizer mounts ONLY while recording, so
  // an idle composer (the SSR default — no effects, isRecording=false) shows the
  // mic but no visualizer. This pins "no static placeholder bars" — the old
  // always-at-rest equalizer that lied about reacting to the mic is gone.
  it('does not render the live mic visualizer while idle (not recording)', () => {
    const html = renderToStaticMarkup(
      <AgentConversationSurface
        conversation={makeConversation()}
        voiceAdapter={withTranscribe}
        voiceVisualizerClassName="og-voice-visualizer"
      />
    );
    // The mic is available...
    expect(html).toContain('data-available');
    // ...but the equalizer (its accessible label / style hook) is absent at rest.
    expect(html).not.toContain('Nivel del micrófono');
    expect(html).not.toContain('og-voice-visualizer');
  });
});

describe('<AgentConversationSurface> showNewChatButton (B3-OG118-5)', () => {
  it('renders the built-in new-chat button by default when a thread exists', () => {
    const html = renderToStaticMarkup(
      <AgentConversationSurface
        conversation={makeConversation()}
        newChatLabel="Nuevo chat"
      />
    );
    expect(html).toContain('Nuevo chat');
  });

  it('omits the built-in new-chat button when showNewChatButton is false', () => {
    const html = renderToStaticMarkup(
      <AgentConversationSurface
        conversation={makeConversation()}
        newChatLabel="Nuevo chat"
        showNewChatButton={false}
      />
    );
    // The button is gone, but the rest of the surface (transcript) still renders.
    expect(html).not.toContain('Nuevo chat');
    expect(html).toContain('pregunta del usuario');
  });
});

describe('<AgentConversationSurface> send button (B3-FIGLASS-6)', () => {
  it('renders a send button by default with the consumer style hook', () => {
    const html = renderToStaticMarkup(
      <AgentConversationSurface
        conversation={makeConversation()}
        sendButtonClassName="og-send-btn"
      />
    );
    expect(html).toContain('Enviar mensaje');
    expect(html).toContain('og-send-btn');
  });

  it('disables the send button when there is no text (idle)', () => {
    // SSR default: input starts empty → canSend false → button disabled.
    const html = renderToStaticMarkup(
      <AgentConversationSurface conversation={makeConversation()} />
    );
    expect(html).toContain('aria-label="Enviar mensaje"');
    expect(html).toContain('disabled');
  });

  it('omits the send button when showSendButton is false', () => {
    const html = renderToStaticMarkup(
      <AgentConversationSurface
        conversation={makeConversation()}
        showSendButton={false}
      />
    );
    expect(html).not.toContain('Enviar mensaje');
  });
});

describe('<AgentConversationSurface> composer input fill (B3-FIGLASS-6)', () => {
  // The width fix belongs to the framework, not a consumer selector reaching
  // into the internal `.relative` wrapper. The surface hands the Composer a
  // wrapperStyle that grows the input, so the textarea fills the composer area
  // regardless of how the consumer styles it.
  it('grows the composer input wrapper to fill (flex grow owned by the surface)', () => {
    const html = renderToStaticMarkup(
      <AgentConversationSurface conversation={makeConversation()} />
    );
    // The inline flex-grow lands on the input wrapper in SSR output.
    expect(html).toMatch(/flex:\s*1 1 0%/);
    expect(html).toMatch(/min-width:\s*0/);
  });
});
