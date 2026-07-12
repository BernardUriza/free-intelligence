// @vitest-environment jsdom
/**
 * Tests for composer focus recovery (B3-FIGLASS-10).
 *
 * The daily-driver audit's "Enter no envía": after clicking the mic/send button,
 * focus stays ON the button, so the next Enter re-triggers the button instead of
 * sending. The surface now refocuses its textarea (via the typed textareaRef)
 * when a turn settles and when dictation finishes transcribing — without
 * fighting a user who focused a different text-entry control.
 *
 * useDictation is mocked so isTranscribing can be driven without a recorder.
 */

import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, cleanup } from '@testing-library/react';
import type { ChatMessage } from '@free-intelligence/core';
import { AgentConversationSurface } from './AgentConversationSurface';
import type { AgentConversation } from './useAgentConversation';

// Controllable dictation state; the rest of ../voice stays real.
const dictationState = {
  isRecording: false,
  isTranscribing: false,
  bands: [] as number[],
  startRecording: vi.fn(),
  stopRecording: vi.fn(async () => {}),
};
vi.mock('../voice', async (importOriginal) => {
  const original = await importOriginal<typeof import('../voice')>();
  return { ...original, useDictation: () => ({ ...dictationState }) };
});

const idleTurn = {
  plan: null,
  steps: [],
  text: '',
  sources: [],
  meta: null,
  status: 'thinking',
} as unknown as AgentConversation['turn'];

const messages: ChatMessage[] = [
  { role: 'user', content: 'hola', timestamp: '2026-01-01T00:00:00Z' },
];

const makeConversation = (over: Partial<AgentConversation> = {}): AgentConversation =>
  ({
    messages,
    turn: idleTurn,
    isStreaming: false,
    turnError: null,
    send: () => {},
    retry: () => {},
    dismissError: () => {},
    persistError: null,
    unsentText: null,
    clearUnsentText: () => {},
    retryPersist: () => {},
    dismissPersistError: () => {},
    newConversation: () => {},
    ...over,
  }) as AgentConversation;

const getComposer = (container: HTMLElement) =>
  container.querySelector('textarea') as HTMLTextAreaElement;

describe('<AgentConversationSurface> focus recovery (B3-FIGLASS-10)', () => {
  afterEach(() => {
    cleanup();
    dictationState.isRecording = false;
    dictationState.isTranscribing = false;
  });

  it('refocuses the composer when streaming ends (clean finish)', () => {
    const { container, rerender } = render(
      <AgentConversationSurface conversation={makeConversation({ isStreaming: true })} />,
    );
    expect(document.activeElement).not.toBe(getComposer(container));

    rerender(
      <AgentConversationSurface conversation={makeConversation({ isStreaming: false })} />,
    );
    expect(document.activeElement).toBe(getComposer(container));
  });

  it('refocuses the composer when the turn fails (recoverable error → edit/retry)', () => {
    const { container, rerender } = render(
      <AgentConversationSurface conversation={makeConversation({ isStreaming: true })} />,
    );
    rerender(
      <AgentConversationSurface
        conversation={makeConversation({
          isStreaming: false,
          turnError: { kind: 'timeout', message: 'tardó demasiado' },
        })}
      />,
    );
    expect(document.activeElement).toBe(getComposer(container));
    // The recoverable banner is rendered alongside.
    expect(container.querySelector('[role="alert"]')?.textContent).toContain('tardó demasiado');
  });

  it('refocuses the composer when dictation finishes transcribing (mic focus trap)', () => {
    const voiceAdapter = {
      defaultVoice: 'nova',
      availableVoices: [],
      synthesize: async () => new Blob(),
      transcribe: async () => ({ text: 'dictado' }),
    };
    dictationState.isTranscribing = true;
    const { container, rerender } = render(
      <AgentConversationSurface conversation={makeConversation()} voiceAdapter={voiceAdapter} />,
    );
    // Simulate the trap: the user's click left focus on the mic button.
    const mic = container.querySelector('[data-fi-mic-slot] button') as HTMLButtonElement;
    mic?.focus();

    dictationState.isTranscribing = false;
    rerender(
      <AgentConversationSurface conversation={makeConversation()} voiceAdapter={voiceAdapter} />,
    );
    expect(document.activeElement).toBe(getComposer(container));
  });

  it('does NOT steal focus from another text-entry control (e.g. a token input)', () => {
    const external = document.createElement('input');
    document.body.appendChild(external);

    const { container, rerender } = render(
      <AgentConversationSurface conversation={makeConversation({ isStreaming: true })} />,
    );
    external.focus();
    rerender(
      <AgentConversationSurface conversation={makeConversation({ isStreaming: false })} />,
    );
    expect(document.activeElement).toBe(external);
    expect(document.activeElement).not.toBe(getComposer(container));
    external.remove();
  });

  it('does not refocus on mount (no streaming transition has happened)', () => {
    const { container } = render(
      <AgentConversationSurface conversation={makeConversation()} />,
    );
    expect(document.activeElement).not.toBe(getComposer(container));
  });
});
