// @vitest-environment jsdom

/**
 * Drawer behavior for AgentWorkspaceShell (B3-FIGLASS-MOBILE-1).
 *
 * FG-4 gave the shell its page-composition slots (header/conversation/rail/
 * footer). This pins the folded-in `sidebar` slot + opt-in mobile drawer:
 *  - no `sidebar` → output is the original page primitive, no drawer chrome;
 *  - `sidebar` on desktop → a static left column, no toggle/overlay;
 *  - `sidebar` + `responsive` on mobile → an off-canvas drawer the hamburger
 *    opens and the overlay/Escape/render-prop close.
 *
 * Static SSR (node env) covers the no-drawer contract in the sibling FG-4 file;
 * the drawer needs jsdom + a matchMedia mock + interaction, so it lives here.
 */

import { afterEach, beforeEach, describe, it, expect, vi } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import { render, cleanup, fireEvent } from '@testing-library/react';
import { clearMediaQueryCache } from '../shell/useMediaQuery';
import { AgentWorkspaceShell } from './AgentWorkspaceShell';

beforeEach(clearMediaQueryCache);
afterEach(cleanup);

function mockMatchMedia(matches: boolean) {
  window.matchMedia = vi.fn().mockImplementation((query: string) => ({
    matches,
    media: query,
    onchange: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })) as unknown as typeof window.matchMedia;
}

const drawerTransform = (container: HTMLElement): string =>
  (container.querySelector('[data-fi-slot="sidebar"][style*="translateX"]') as HTMLElement)?.style.transform ?? '';

describe('AgentWorkspaceShell — no sidebar (original page primitive)', () => {
  it('renders no drawer chrome and no sidebar slot', () => {
    mockMatchMedia(false);
    const html = renderToStaticMarkup(
      <AgentWorkspaceShell conversation={<main>chat</main>} />,
    );
    expect(html).toContain('<main>chat</main>');
    expect(html).not.toContain('fi-aws-toggle');
    expect(html).not.toContain('data-fi-slot="sidebar"');
    expect(html).not.toContain('translateX');
  });
});

describe('AgentWorkspaceShell — sidebar on desktop', () => {
  it('renders a static sidebar column, no toggle/overlay', () => {
    mockMatchMedia(false);
    const html = renderToStaticMarkup(
      <AgentWorkspaceShell
        sidebar={<nav>list</nav>}
        sidebarWidth={320}
        conversation={<main>chat</main>}
      />,
    );
    expect(html).toContain('data-fi-slot="sidebar"');
    expect(html).toContain('width:320px');
    expect(html).toContain('<nav>list</nav>');
    expect(html).not.toContain('fi-aws-toggle');
    expect(html).not.toContain('translateX');
  });

  it('passes the drawer api to a render-function sidebar', () => {
    mockMatchMedia(false);
    const html = renderToStaticMarkup(
      <AgentWorkspaceShell
        responsive
        sidebar={(api) => <nav>{api.isMobile ? 'mobile' : 'desktop'}</nav>}
        conversation={<main />}
      />,
    );
    expect(html).toContain('<nav>desktop</nav>');
  });
});

describe('AgentWorkspaceShell — mobile drawer (responsive)', () => {
  it('starts off-canvas, opens via the toggle, closes on Escape', () => {
    mockMatchMedia(true);
    const { container } = render(
      <AgentWorkspaceShell responsive sidebar={<nav>list</nav>} conversation={<main>chat</main>} />,
    );
    expect(drawerTransform(container)).toBe('translateX(-100%)');

    fireEvent.click(container.querySelector('.fi-aws-toggle') as HTMLElement);
    expect(drawerTransform(container)).toBe('translateX(0)');

    fireEvent.keyDown(document, { key: 'Escape' });
    expect(drawerTransform(container)).toBe('translateX(-100%)');
  });

  it('closes via the render-prop api (selection)', () => {
    mockMatchMedia(true);
    const { container, getByText } = render(
      <AgentWorkspaceShell
        responsive
        sidebar={(api) => (
          <nav>
            <button onClick={api.close}>pick</button>
          </nav>
        )}
        conversation={<main>chat</main>}
      />,
    );
    fireEvent.click(container.querySelector('.fi-aws-toggle') as HTMLElement);
    expect(drawerTransform(container)).toBe('translateX(0)');

    fireEvent.click(getByText('pick'));
    expect(drawerTransform(container)).toBe('translateX(-100%)');
  });
});
