// @vitest-environment jsdom
/**
 * Contract test for the contained-layout mode (FG-1, canary-driven upstream).
 *
 * THE LIMIT (captured by a real consumer, activist-os): the surface root hard-
 * codes `height: 100dvh` (AgentConversationSurface.tsx:351), so it CANNOT be
 * composed inside a fixed-height app shell (header + main + artifacts rail +
 * footer). A 100dvh child inside a `height: 640px` grid cell overflows its cell
 * and forces page scroll instead of scrolling its own transcript internally.
 *
 * THE CONTRACT this pins: a `layout` prop selects how the root sizes itself.
 *  - `layout="viewport"` (DEFAULT, backward-compatible): root = `height: 100dvh`
 *    (the current full-page behavior, unchanged for every existing consumer).
 *  - `layout="contained"`: root = `height: 100%` + `minHeight: 0` +
 *    `overflow: hidden`, so it fills WHATEVER fixed-height cell the app shell
 *    gives it and scrolls the transcript region internally, never the page.
 *
 * jsdom does no layout, so "scrolls internally" is pinned as its mechanism: the
 * root clips, one box scrolls, and every box between them can shrink.
 */

import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import { renderToStaticMarkup } from 'react-dom/server';
import { AgentConversationSurface } from './AgentConversationSurface';
import type { AgentConversation } from './useAgentConversation';

const conversation = {
  messages: [
    { role: 'user', content: 'hola', timestamp: '2026-06-18T00:00:00Z' },
    { role: 'assistant', content: 'mundo', timestamp: '2026-06-18T00:00:01Z' },
  ],
  turn: {
    plan: null,
    steps: [],
    text: '',
    sources: [],
    meta: null,
    status: 'complete',
  },
  isStreaming: false,
  turnError: null,
    turnNotice: null,
    dismissNotice: () => {},
  send: () => {},
  retry: () => {},
  dismissError: () => {},
  newConversation: () => {},
  author: { id: 'agent', name: 'og118', symbol: 'og' },
} as unknown as AgentConversation;

function renderContained(): HTMLElement {
  const { container } = render(
    <AgentConversationSurface conversation={conversation} layout="contained" />,
  );
  return container.firstElementChild as HTMLElement;
}

describe('<AgentConversationSurface> respects contained parent height (FG-1)', () => {
  it('layout="viewport" (default) keeps the full-page 100dvh root (backward-compatible)', () => {
    const html = renderToStaticMarkup(
      <AgentConversationSurface conversation={conversation} layout="viewport" />,
    );
    const rootNode = html.match(/^<div[^>]*>/)?.[0];
    expect(rootNode).toBeTruthy();
    expect(rootNode).toContain('height:100dvh');
  });

  it('layout="contained" does NOT hardcode 100dvh — it fills its parent cell with height:100%', () => {
    const root = renderContained();
    expect(root.style.height).toBe('100%');
    expect(root.getAttribute('style')).not.toContain('100dvh');
  });

  it('layout="contained" makes the transcript the scroll container, not the page', () => {
    const root = renderContained();
    expect(root.style.overflow).toBe('hidden');
    expect(parseFloat(root.style.minHeight)).toBe(0);

    const scroller = Array.from(root.querySelectorAll<HTMLElement>('*')).find(
      (el) => el.style.overflowY === 'auto',
    );
    expect(scroller, 'no element under the root scrolls').toBeTruthy();
    expect(scroller!.style.flex).toMatch(/^1/);

    // A flex item defaults to min-height:auto and grows to its content, so ONE box
    // between the root and the scroller without min-height:0 pushes the scroll to the page.
    for (let box = scroller!.parentElement; box && box !== root; box = box.parentElement) {
      expect(parseFloat(box.style.minHeight), box.outerHTML.slice(0, 80)).toBe(0);
    }
  });
});
