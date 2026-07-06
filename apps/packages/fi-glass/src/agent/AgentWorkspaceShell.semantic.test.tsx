// @vitest-environment jsdom

/**
 * Semantic landmarks for AgentWorkspaceShell (B3-FIGLASS-SEMANTIC-SHELL-1, PR3).
 *
 * The shell composed its slots from inline-flex `<div data-fi-slot>`s — no DOM
 * landmarks. This pins the semantic upgrade: header/main/aside/footer for the page
 * column, and a labelled `<nav>` for the sidebar — visual-equivalent (the inline
 * styles and `data-fi-slot` attributes are preserved), so consumers need no CSS.
 */

import { describe, expect, it } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import { AgentWorkspaceShell } from './AgentWorkspaceShell';

describe('B3-FIGLASS-SEMANTIC-SHELL-1 · landmarks', () => {
  it('wraps header/main/rail/footer slots in semantic elements', () => {
    const html = renderToStaticMarkup(
      <AgentWorkspaceShell
        header={<span>h</span>}
        conversation={<span>c</span>}
        rail={<span>r</span>}
        footer={<span>f</span>}
      />,
    );
    expect(html).toContain('<header data-fi-slot="header">');
    expect(html).toContain('<main data-fi-slot="main"');
    expect(html).toContain('<aside data-fi-slot="rail"');
    expect(html).toContain('<footer data-fi-slot="footer">');
  });

  it('renders the sidebar as a labelled nav landmark (not a bare div)', () => {
    const html = renderToStaticMarkup(
      <AgentWorkspaceShell
        sidebar={<span>s</span>}
        conversation={<span>c</span>}
        toggleLabel="Conversaciones"
      />,
    );
    expect(html).toContain('data-fi-slot="sidebar"');
    expect(html).toMatch(/<nav[^>]*data-fi-slot="sidebar"/);
    expect(html).toContain('aria-label="Conversaciones"');
  });

  it('keeps the slot data attributes (selectors + styling unchanged)', () => {
    const html = renderToStaticMarkup(
      <AgentWorkspaceShell conversation={<span>c</span>} />,
    );
    expect(html).toContain('data-fi-slot="conversation"');
    expect(html).toContain('data-fi-workspace="agent"');
  });
});
