/**
 * Tests for the viewport scroll-container contract (B3-FIGLASS-15).
 *
 * The scrollbar must render at the VIEWPORT edge, not glued to the centered
 * column: overflow-y lives on a full-width container, while the fluid center
 * cap (100% minus a 60px gutter) lives on INNER content wrappers (transcript +
 * composer column). These SSR assertions pin that structure so the overflow
 * never silently moves back onto a width-capped node.
 */

import { describe, it, expect } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import { AgentConversationSurface } from './AgentConversationSurface';
import type { AgentConversation } from './useAgentConversation';

const conversation = {
  messages: [
    { role: 'user', content: 'hola', timestamp: '2026-06-12T00:00:00Z' },
    { role: 'assistant', content: 'mundo', timestamp: '2026-06-12T00:00:01Z' },
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

describe('<AgentConversationSurface> viewport scroll container (B3-FIGLASS-15)', () => {
  const html = renderToStaticMarkup(
    <AgentConversationSurface conversation={conversation} />,
  );

  it('keeps the scroll container full-width (no max-width on the overflow node)', () => {
    const overflowNode = html.match(/<div[^>]*overflow-y:auto[^>]*>/)?.[0];
    expect(overflowNode).toBeTruthy();
    expect(overflowNode).not.toContain('max-width');
  });

  it('caps the transcript and the composer column fluidly via inner wrappers', () => {
    const caps = html.match(/max-width:calc\(100% - 60px\)/g) ?? [];
    // One for the transcript content wrapper + one for the composer column.
    expect(caps.length).toBe(2);
  });

  it('the root no longer carries the center cap', () => {
    const rootNode = html.match(/^<div[^>]*>/)?.[0];
    expect(rootNode).toBeTruthy();
    expect(rootNode).not.toContain('max-width');
  });
});
