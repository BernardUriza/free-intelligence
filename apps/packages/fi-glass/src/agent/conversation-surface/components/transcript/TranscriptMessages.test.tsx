// @vitest-environment jsdom
/**
 * Tests for the live glass-box rail (B3-FIGLASS-LIVE-TRACE-STICKY-1).
 *
 * The defect this pins: the streaming turn's AgentPanel scrolled away with the
 * answer. On a real og118 turn the plan sat at y = -2921px — off-screen — so
 * "watch it plan" broke on exactly the long, multi-step answers a plan exists
 * for. The live panel now sticks to the top of the transcript's scroll
 * viewport; the PERSISTED trace does not (it is history, read by scrolling up).
 */

import { describe, it, expect, afterEach } from 'vitest';
import { render, cleanup } from '@testing-library/react';
import type { AgentTurnState, ChatMessage } from '@free-intelligence/core';
import { TranscriptMessages } from './TranscriptMessages';

const turn = (over: Partial<AgentTurnState> = {}): AgentTurnState => ({
  plan: { steps: [{ label: 'paso uno', status: 'running' }] },
  steps: [],
  text: 'respondiendo',
  sources: [],
  meta: null,
  author: null,
  heartbeats: 0,
  status: 'thinking',
  ...over,
});

const AGENT_AUTHOR = { id: 'og118', name: 'og118', symbol: 'og' };

const base = {
  turn: turn(),
  agentAuthor: AGENT_AUTHOR,
  showPersistedTrace: true,
  showCopyAction: false,
  resolveBubbleClass: () => undefined,
  collapseUserMessages: false,
};

const liveRail = () => document.querySelector('[data-fi-live-trace]');

describe('<TranscriptMessages> live glass-box rail', () => {
  afterEach(cleanup);

  it('pins the streaming turn\'s panel to the top of the scroll viewport', () => {
    render(<TranscriptMessages {...base} messages={[]} isStreaming />);
    const rail = liveRail() as HTMLElement;
    expect(rail).not.toBeNull();
    expect(rail.style.position).toBe('sticky');
    expect(rail.style.top).toBe('0px');
  });

  it('renders the plan inside the sticky rail, not beside it', () => {
    render(<TranscriptMessages {...base} messages={[]} isStreaming />);
    expect(liveRail()!.textContent).toContain('paso uno');
  });

  // A sticky element only travels inside its own parent. When the rail was a
  // lone child of the transcript column its runway was ~0 and it scrolled off
  // regardless of `position: sticky` — verified in a real browser. The
  // streaming answer must share the rail's parent so its height IS the runway.
  it('shares one parent with the streaming answer, so the rail has a runway', () => {
    render(<TranscriptMessages {...base} messages={[]} isStreaming />);
    const rail = liveRail()!;
    const answer = document.body.textContent!.includes('respondiendo');
    expect(answer).toBe(true);
    const wrapper = rail.parentElement!;
    // the answer bubble is a sibling of the rail, not an uncle
    expect(wrapper.children.length).toBeGreaterThan(1);
    expect(wrapper.textContent).toContain('respondiendo');
  });

  it('mounts no rail when nothing is streaming', () => {
    render(<TranscriptMessages {...base} messages={[]} isStreaming={false} />);
    expect(liveRail()).toBeNull();
  });

  // The persisted trace is history: it belongs above its own answer and must
  // NOT stick, or every past turn would fight for the top of the viewport.
  it('never sticks a persisted trace', () => {
    const message: ChatMessage = {
      role: 'assistant',
      content: 'ya respondí',
      timestamp: '2026-07-09T12:00:00Z',
      trace: { plan: { steps: [{ label: 'paso viejo', status: 'done' }] }, steps: [], sources: [] },
    } as ChatMessage;
    render(<TranscriptMessages {...base} messages={[message]} isStreaming={false} />);
    expect(liveRail()).toBeNull();
    expect(document.body.textContent).toContain('paso viejo');
  });
});

describe('<TranscriptMessages> authorship — the bubble names WHO spoke', () => {
  afterEach(cleanup);

  const YODO = { id: 'element-053-i-yodo', name: 'Yodo', symbol: 'I', engine: 'Insult' };

  it('renders the message author, not the app name (the og118 bug)', () => {
    render(
      <TranscriptMessages
        {...base}
        isStreaming={false}
        messages={[
          {
            role: 'assistant',
            author: YODO,
            content: 'respuesta de Yodo',
            timestamp: '2026-07-11T04:00:00Z',
          },
        ]}
      />,
    );
    expect(document.body.textContent).toContain('Yodo');
    expect(document.body.textContent).not.toContain('og118');
  });

  it('attributes the LIVE streaming bubble to the announced speaker', () => {
    render(
      <TranscriptMessages
        {...base}
        turn={turn({ author: YODO, text: 'escribiendo…' })}
        isStreaming
        messages={[]}
      />,
    );
    expect(document.body.textContent).toContain('Yodo');
  });

  it('falls back to the agent identity when no speaker was announced', () => {
    render(
      <TranscriptMessages
        {...base}
        turn={turn({ author: null,
  heartbeats: 0, text: 'hola' })}
        isStreaming
        messages={[]}
      />,
    );
    expect(document.body.textContent).toContain('og118');
  });
});

describe('<TranscriptMessages> model provenance — the chip the consumer never got to show', () => {
  afterEach(cleanup);

  it('renders "powered by <model>" off the persisted trace', () => {
    render(
      <TranscriptMessages
        {...base}
        isStreaming={false}
        messages={[
          {
            role: 'assistant',
            author: AGENT_AUTHOR,
            content: 'hola',
            timestamp: '2026-07-11T04:00:00Z',
            trace: { model: 'claude-sonnet-4-6' },
          },
        ]}
      />,
    );
    const badge = document.querySelector('[data-fi-model-badge]');
    expect(badge).not.toBeNull();
    expect(badge?.textContent).toContain('claude-sonnet-4-6');
  });

  it('shows no chip when the turn recorded no model', () => {
    render(
      <TranscriptMessages
        {...base}
        isStreaming={false}
        messages={[
          {
            role: 'assistant',
            author: AGENT_AUTHOR,
            content: 'hola',
            timestamp: '2026-07-11T04:00:00Z',
          },
        ]}
      />,
    );
    expect(document.querySelector('[data-fi-model-badge]')).toBeNull();
  });
});
