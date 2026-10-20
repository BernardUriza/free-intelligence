// @vitest-environment jsdom
/**
 * FIGLASS-STATE-RESIDUALS-1 #2 — the composer gates on the SAME predicate `send`
 * uses. After a watchdog timeout on a transport that cannot abort, the
 * conversation stops "streaming" while the transport is still busy; the surface
 * used to clear the box and then watch `send` refuse, losing what the user wrote.
 */

import { useCallback, useState } from 'react';
import { describe, it, expect, afterEach, vi } from 'vitest';
import { act, cleanup, fireEvent, render, renderHook, waitFor } from '@testing-library/react';
import type { AgentHook, AgentTurnState, MessageImage } from '@free-intelligence/core';
import { AgentConversationSurface } from './AgentConversationSurface';
import { useAgentConversation, type AgentConversation } from './useAgentConversation';

const AUTHOR = { id: 'og118', name: 'og118', symbol: 'og' };

const thinking: AgentTurnState = {
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

function useHungAgent(): AgentHook {
  const [isStreaming, setStreaming] = useState(false);
  const send = useCallback(async () => setStreaming(true), []);
  return { turn: thinking, isStreaming, send, reset: () => {} };
}

function Harness() {
  const conversation = useAgentConversation(useHungAgent(), { author: AUTHOR, turnTimeoutMs: 20 });
  return <AgentConversationSurface conversation={conversation} />;
}

const box = (c: HTMLElement) => c.querySelector('textarea') as HTMLTextAreaElement;
const sendButton = (c: HTMLElement) =>
  c.querySelector('[data-fi-composer-send-state]') as HTMLButtonElement;

describe('<AgentConversationSurface> send gate', () => {
  afterEach(cleanup);

  it('a timeout on a busy transport never wipes the next draft', async () => {
    const { container } = render(<Harness />);
    fireEvent.change(box(container), { target: { value: 'primera' } });
    await act(async () => {
      fireEvent.click(sendButton(container));
    });
    await waitFor(() =>
      expect(container.querySelector('[role="alert"]')?.textContent).toContain('tardó demasiado'),
    );

    fireEvent.change(box(container), { target: { value: 'segunda' } });
    await act(async () => {
      fireEvent.click(sendButton(container));
    });
    expect(box(container).value).toBe('segunda');
    expect(sendButton(container).disabled).toBe(true);
  });
});

describe('useAgentConversation — one can-send predicate', () => {
  it('canSend follows the transport, and send reports whether it went out', async () => {
    const { result } = renderHook(() =>
      useAgentConversation(useHungAgent(), { author: AUTHOR, turnTimeoutMs: 0 }),
    );
    expect(result.current.canSend).toBe(true);
    let accepted: boolean | undefined;
    await act(async () => {
      accepted = result.current.send('hola');
    });
    expect(accepted).toBe(true);
    expect(result.current.canSend).toBe(false);
    await act(async () => {
      accepted = result.current.send('otra');
    });
    expect(accepted).toBe(false);
  });
});

describe('<AgentConversationSurface> image still encoding (FIGLASS-STATE-RESIDUALS-1 #5)', () => {
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it('holds the send until the picked image is ready, then sends it WITH this message', async () => {
    const release: Array<() => void> = [];
    const Real = globalThis.FileReader;
    vi.stubGlobal(
      'FileReader',
      class extends Real {
        readAsDataURL(blob: Blob) {
          release.push(() => super.readAsDataURL(blob));
        }
      },
    );
    const sent: Array<{ text: string; images?: MessageImage[] }> = [];
    const conversation = {
      messages: [],
      turn: thinking,
      author: AUTHOR,
      isStreaming: false,
      canSend: true,
      turnError: null,
      turnNotice: null,
      dismissNotice: () => {},
      persistError: null,
      retryPersist: () => {},
      dismissPersistError: () => {},
      unsentText: null,
      unsentImages: null,
      clearUnsent: () => {},
      send: (text: string, images?: MessageImage[]) => {
        sent.push({ text, images });
        return true;
      },
      sendAndAwait: async () => '',
      retry: () => {},
      dismissError: () => {},
      newConversation: () => {},
    } as AgentConversation;
    const { container } = render(<AgentConversationSurface conversation={conversation} imageAttachments />);
    const file = new File([Uint8Array.from([0x89, 0x50, 0x4e, 0x47])], 'foto.png', { type: 'image/png' });
    await act(async () => {
      fireEvent.change(container.querySelector('input[type="file"]') as HTMLInputElement, {
        target: { files: [file] },
      });
    });
    fireEvent.change(box(container), { target: { value: 'mira esto' } });
    await act(async () => {
      fireEvent.click(sendButton(container));
    });
    expect(sent).toHaveLength(0);
    expect(box(container).value).toBe('mira esto');

    await act(async () => {
      release.forEach((go) => go());
    });
    await waitFor(() => expect(sendButton(container).disabled).toBe(false));
    await act(async () => {
      fireEvent.click(sendButton(container));
    });
    expect(sent).toHaveLength(1);
    expect(sent[0].text).toBe('mira esto');
    expect(sent[0].images).toHaveLength(1);
  });
});
