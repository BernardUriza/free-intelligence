/**
 * Contract test for AgentWorkspaceShell (FG-3, canary-driven upstream loop).
 *
 * THE NEXT LIMIT (captured by the real consumer, activist-os): FG-1/FG-2 gave
 * AgentConversationSurface a `layout="contained"` mode so it can live inside a
 * fixed-height cell. But every consumer still hand-rolls the PAGE that wraps it
 * — the header + main grid + conversation column + artifact rail + footer, all
 * viewport-locked with no page overflow and mobile stacking. activist-os's
 * FiGlassPrimary is exactly that hand-rolled shell.
 *
 * THE CONTRACT this pins: a fi-glass primitive `AgentWorkspaceShell` that
 * COMPOSES a full agent-workspace page from slots — turning fi-glass into a
 * page-composition system (eventually declarative AgentAppScreen templates):
 *
 *  - a workspace ROOT that locks to the viewport with no page overflow;
 *  - named slots: header / main / conversation / rail / footer;
 *  - the MAIN region carries the contained contract (`min-height:0` +
 *    `overflow:hidden`) so its children scroll internally, never the page;
 *  - the CONVERSATION region is contained (NOT `100dvh`) — it fills its cell;
 *  - the RAIL region scrolls internally (`overflow-y:auto`/`overflow:auto` +
 *    `min-height:0`), so a tall artifact list never grows the page;
 *  - a VISUAL variant marker (e.g. `aurora`) — class or data- attribute;
 *  - a DENSITY marker (e.g. `comfortable`) — class or data- attribute.
 *
 * Static SSR markup is enough (jsdom has no layout engine — same constraint as
 * FG-1/FG-2): we assert on the rendered slot markers, inline style and
 * attributes the shell carries, never on computed layout.
 *
 * RED PHASE: `AgentWorkspaceShell` does not exist yet. The import below fails to
 * resolve (missing module + TS error), so the whole file is RED for a real
 * reason — the contract is captured, the implementation (FG-4) is a later step.
 */

import { describe, it, expect } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import { AgentConversationSurface } from './AgentConversationSurface';
import { AgentWorkspaceShell } from './AgentWorkspaceShell';
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
  author: { id: 'agent', name: 'og118', symbol: 'og' },
} as unknown as AgentConversation;

const renderShell = () =>
  renderToStaticMarkup(
    <AgentWorkspaceShell
      visual="aurora"
      density="comfortable"
      header={<div data-testid="header" />}
      conversation={
        <AgentConversationSurface conversation={conversation} layout="contained" />
      }
      rail={<div data-testid="rail" />}
      footer={<div data-testid="footer" />}
    />,
  );

describe('<AgentWorkspaceShell> composes a viewport-locked agent workspace (FG-3)', () => {
  it('renders a workspace root', () => {
    const html = renderShell();
    const rootNode = html.match(/^<div[^>]*>/)?.[0];
    expect(rootNode).toBeTruthy();
    // The root identifies itself as the workspace shell (class or data marker).
    expect(rootNode).toMatch(/fi-(?:agent-)?workspace|data-fi-workspace|data-fi-shell/);
  });

  it('exposes every named slot (header / main / conversation / rail / footer)', () => {
    const html = renderShell();
    // The caller-provided slot content is rendered...
    expect(html).toContain('data-testid="header"');
    expect(html).toContain('data-testid="rail"');
    expect(html).toContain('data-testid="footer"');
    // ...and the shell tags each region with a slot marker.
    expect(html).toMatch(/data-fi-slot="header"|fi-workspace-header/);
    expect(html).toMatch(/data-fi-slot="main"|fi-workspace-main/);
    expect(html).toMatch(/data-fi-slot="conversation"|fi-workspace-conversation/);
    expect(html).toMatch(/data-fi-slot="rail"|fi-workspace-rail/);
    expect(html).toMatch(/data-fi-slot="footer"|fi-workspace-footer/);
  });

  it('the main region carries the contained contract (min-height:0 + overflow:hidden)', () => {
    const html = renderShell();
    const mainNode =
      html.match(/<[a-z]+[^>]*data-fi-slot="main"[^>]*>/)?.[0] ??
      html.match(/<[a-z]+[^>]*fi-workspace-main[^>]*>/)?.[0];
    expect(mainNode).toBeTruthy();
    expect(mainNode).toContain('min-height:0');
    expect(mainNode).toContain('overflow:hidden');
  });

  it('the conversation region is contained — it never forces the viewport height', () => {
    const html = renderShell();
    const conversationNode =
      html.match(/<[a-z]+[^>]*data-fi-slot="conversation"[^>]*>/)?.[0] ??
      html.match(/<[a-z]+[^>]*fi-workspace-conversation[^>]*>/)?.[0];
    expect(conversationNode).toBeTruthy();
    // Contained = fills its cell, never 100dvh (which would overflow the shell
    // and bring back page scroll, the exact FG-1/FG-2 limit).
    expect(conversationNode).not.toContain('100dvh');
    expect(conversationNode).toContain('min-height:0');
  });

  it('the rail region scrolls internally so a tall artifact list never grows the page', () => {
    const html = renderShell();
    const railNode =
      html.match(/<[a-z]+[^>]*data-fi-slot="rail"[^>]*>/)?.[0] ??
      html.match(/<[a-z]+[^>]*fi-workspace-rail[^>]*>/)?.[0];
    expect(railNode).toBeTruthy();
    expect(railNode).toMatch(/overflow-y:auto|overflow:auto/);
    expect(railNode).toContain('min-height:0');
  });

  it('carries a visual variant marker for "aurora"', () => {
    const html = renderShell();
    const rootNode = html.match(/^<div[^>]*>/)?.[0];
    expect(rootNode).toBeTruthy();
    expect(rootNode).toMatch(/data-fi-visual="aurora"|fi-visual-aurora|aurora/);
  });

  it('carries a density marker for "comfortable"', () => {
    const html = renderShell();
    const rootNode = html.match(/^<div[^>]*>/)?.[0];
    expect(rootNode).toBeTruthy();
    expect(rootNode).toMatch(/data-fi-density="comfortable"|fi-density-comfortable|comfortable/);
  });
});
