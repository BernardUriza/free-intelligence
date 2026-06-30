// @vitest-environment jsdom
/**
 * Tests for the sidebar section primitive (B3-FIGLASS-SHELL-PRIMITIVES-1C).
 *
 * Pins the header anatomy og118 hand-wrote twice (og-sidebar-head + og-projects-head):
 * a string title wrapped in the title slot (a node used as-is for branding), an
 * action slot in the head, and the count→empty gate — `emptyState` shows only when
 * `count === 0` AND an empty state was supplied, otherwise `children` always render.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, cleanup } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach } from 'vitest';
import { AgentSidebarSection } from './AgentSidebarSection';
import { FI_SECTION_TITLE_CLASS } from './sidebarSectionStyle';

afterEach(cleanup);

describe('AgentSidebarSection', () => {
  it('wraps a string title in the title slot and exposes the section by aria-label', () => {
    render(
      <AgentSidebarSection title="Proyectos" count={1} ariaLabel="Proyectos">
        <nav>rows</nav>
      </AgentSidebarSection>,
    );
    const title = screen.getByText('Proyectos');
    expect(title.className).toContain(FI_SECTION_TITLE_CLASS);
    expect(screen.getByRole('region', { name: 'Proyectos' })).toBeTruthy();
  });

  it('uses a node title as-is (branding) — not wrapped in the title slot', () => {
    render(
      <AgentSidebarSection
        title={<span data-testid="brand">og118<span>.ai</span></span>}
        count={1}
      >
        <nav>rows</nav>
      </AgentSidebarSection>,
    );
    const brand = screen.getByTestId('brand');
    expect(brand.className).not.toContain(FI_SECTION_TITLE_CLASS);
    expect(brand.textContent).toBe('og118.ai');
  });

  it('renders the action slot in the head and fires its handler', async () => {
    const user = userEvent.setup();
    const onNew = vi.fn();
    render(
      <AgentSidebarSection
        title="Proyectos"
        count={0}
        actionSlot={
          <button onClick={onNew} aria-label="Nuevo proyecto">
            + Nuevo
          </button>
        }
      >
        <nav>rows</nav>
      </AgentSidebarSection>,
    );
    await user.click(screen.getByRole('button', { name: 'Nuevo proyecto' }));
    expect(onNew).toHaveBeenCalledTimes(1);
  });

  it('shows emptyState when count is 0 and hides children', () => {
    render(
      <AgentSidebarSection
        title="Proyectos"
        count={0}
        emptyState={<p>Crea un proyecto</p>}
      >
        <nav data-testid="rows">rows</nav>
      </AgentSidebarSection>,
    );
    expect(screen.getByText('Crea un proyecto')).toBeTruthy();
    expect(screen.queryByTestId('rows')).toBeNull();
  });

  it('shows children when count > 0 even if an emptyState was supplied', () => {
    render(
      <AgentSidebarSection
        title="Proyectos"
        count={2}
        emptyState={<p>Crea un proyecto</p>}
      >
        <nav data-testid="rows">rows</nav>
      </AgentSidebarSection>,
    );
    expect(screen.getByTestId('rows')).toBeTruthy();
    expect(screen.queryByText('Crea un proyecto')).toBeNull();
  });

  it('always renders children when count is 0 but no emptyState is supplied', () => {
    render(
      <AgentSidebarSection title="og118.ai" count={0}>
        <nav data-testid="rows">rows</nav>
      </AgentSidebarSection>,
    );
    expect(screen.getByTestId('rows')).toBeTruthy();
  });

  it('replaces the default head with headerSlot when provided (no title/action rendered)', () => {
    render(
      <AgentSidebarSection
        title="Ignorado"
        count={1}
        actionSlot={<button aria-label="Ignorado">x</button>}
        headerSlot={<header data-testid="custom-head">Custom</header>}
      >
        <nav>rows</nav>
      </AgentSidebarSection>,
    );
    expect(screen.getByTestId('custom-head')).toBeTruthy();
    expect(screen.queryByText('Ignorado')).toBeNull();
    expect(screen.queryByRole('button', { name: 'Ignorado' })).toBeNull();
  });

  // B3-FIGLASS-SIDEBAR-SECTIONS-2 (PR4): card variant + footerSlot
  it('defaults to the plain variant (no card class) — backward-compatible', () => {
    const { container } = render(
      <AgentSidebarSection title="Proyectos" count={1} ariaLabel="P">
        <nav>rows</nav>
      </AgentSidebarSection>,
    );
    expect(container.querySelector('.fi-sidebar-section--card')).toBeNull();
  });

  it('applies the card class when variant="card"', () => {
    const { container } = render(
      <AgentSidebarSection title="Proyectos" count={1} variant="card" ariaLabel="P">
        <nav>rows</nav>
      </AgentSidebarSection>,
    );
    expect(container.querySelector('.fi-sidebar-section--card')).toBeTruthy();
  });

  it('renders footerSlot below the rows in a divider-separated footer', () => {
    render(
      <AgentSidebarSection
        title="Proyectos"
        count={2}
        footerSlot={<div data-testid="upload">upload</div>}
      >
        <nav data-testid="rows">rows</nav>
      </AgentSidebarSection>,
    );
    const footer = screen.getByTestId('upload').parentElement!;
    expect(footer.className).toContain('fi-sidebar-section-footer');
    expect(screen.getByTestId('rows')).toBeTruthy();
  });

  it('omits the footer wrapper entirely when footerSlot is absent', () => {
    const { container } = render(
      <AgentSidebarSection title="Proyectos" count={1}>
        <nav>rows</nav>
      </AgentSidebarSection>,
    );
    expect(container.querySelector('.fi-sidebar-section-footer')).toBeNull();
  });
});
