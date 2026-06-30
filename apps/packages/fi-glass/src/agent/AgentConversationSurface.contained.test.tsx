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
 * Static SSR markup is enough (no jsdom layout engine needed): we assert on the
 * inline style the root carries — exactly how the B3-FIGLASS-15 viewport scroll
 * test (AgentConversationSurface.scroll.test.tsx) pins the root.
 *
 * RED PHASE: the `layout` prop does not exist yet, so `layout="contained"` is
 * ignored and the root still renders `height:100dvh`. These assertions FAIL on
 * purpose. FG-1 only captures the contract; the fix is a later step.
 */

import { describe, it, expect } from 'vitest';
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
  send: () => {},
  retry: () => {},
  dismissError: () => {},
  newConversation: () => {},
} as unknown as AgentConversation;

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
    const html = renderToStaticMarkup(
      <AgentConversationSurface conversation={conversation} layout="contained" />,
    );
    const rootNode = html.match(/^<div[^>]*>/)?.[0];
    expect(rootNode).toBeTruthy();
    // The contained contract: the root must NOT force the viewport height,
    // otherwise it overflows a fixed-height app-shell cell and scrolls the page.
    expect(rootNode).not.toContain('100dvh');
    // It fills whatever fixed-height cell the shell gives it instead.
    expect(rootNode).toContain('height:100%');
  });

  it('layout="contained" clips at the root so the transcript scrolls internally, not the page', () => {
    const html = renderToStaticMarkup(
      <AgentConversationSurface conversation={conversation} layout="contained" />,
    );
    const rootNode = html.match(/^<div[^>]*>/)?.[0];
    expect(rootNode).toBeTruthy();
    expect(rootNode).toContain('min-height:0');
    expect(rootNode).toContain('overflow:hidden');
  });
});
