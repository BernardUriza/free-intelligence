// @vitest-environment jsdom
/**
 * The trail back out of a detail (FIGLASS-PROJECTS-PAGE-1).
 *
 * `aria-current="page"` on the LAST crumb is the point: without it a screen
 * reader announces every crumb as an equal link and never says which one is
 * where you already are.
 */

import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { WorkspaceBreadcrumb } from './WorkspaceBreadcrumb';

afterEach(cleanup);

describe('WorkspaceBreadcrumb', () => {
  it('marks only the last crumb as the current page', () => {
    render(
      <WorkspaceBreadcrumb
        ariaLabel="Migas"
        crumbs={[{ label: 'Índice', href: '/i' }, { label: 'Detalle' }]}
      />,
    );

    expect(screen.getByRole('link', { name: 'Índice' }).getAttribute('aria-current')).toBeNull();
    expect(screen.getByText('Detalle').getAttribute('aria-current')).toBe('page');
  });

  it('renders an inert crumb as plain text, not a dead link', () => {
    render(<WorkspaceBreadcrumb ariaLabel="Migas" crumbs={[{ label: 'Solo' }]} />);

    expect(screen.queryByRole('link')).toBeNull();
    expect(screen.queryByRole('button')).toBeNull();
  });

  it('a crumb with only onClick is a button', async () => {
    const onClick = vi.fn();
    render(
      <WorkspaceBreadcrumb
        ariaLabel="Migas"
        crumbs={[{ label: 'Volver', onClick }, { label: 'Aquí' }]}
      />,
    );

    await userEvent.click(screen.getByRole('button', { name: 'Volver' }));

    expect(onClick).toHaveBeenCalledOnce();
  });

  it('hides the separator from the accessibility tree', () => {
    const { container } = render(
      <WorkspaceBreadcrumb ariaLabel="Migas" crumbs={[{ label: 'A', href: '/a' }, { label: 'B' }]} />,
    );

    const sep = container.querySelector('[aria-hidden="true"]');
    expect(sep?.textContent).toBe('/');
  });

  it('names the navigation landmark', () => {
    render(<WorkspaceBreadcrumb ariaLabel="Migas" crumbs={[{ label: 'A' }]} />);

    expect(screen.getByRole('navigation', { name: 'Migas' })).toBeTruthy();
  });
});

describe('the touch minimum a real-device measurement caught', () => {
  /**
   * Measured in Chrome at a 390px viewport, the crumbs came out **20px tall** and
   * the search box 40 — both under the 44 the repo requires, and both invisible
   * to jsdom, which does no layout. The fix composes the framework minimum; this
   * pins that it is still composed, since the next person to touch the markup
   * cannot re-run that measurement from a unit test.
   */
  it('composes the framework touch minimum onto an actionable crumb', () => {
    const { container } = render(
      <WorkspaceBreadcrumb
        ariaLabel="Migas"
        crumbs={[{ label: 'Índice', onClick: () => {} }, { label: 'Aquí' }]}
      />,
    );

    expect(container.querySelector('button.fi-touch-target')).not.toBeNull();
  });

  it('raises the search box to the minimum on touch surfaces', async () => {
    const { ensureResourceStyle } = await import('./resourceStyle');
    const { FI_TOUCH_QUERY } = await import('../theme/breakpoints');
    ensureResourceStyle();

    const css = document.getElementById('fi-resource-style')?.textContent ?? '';
    const touchBlock = css.slice(css.indexOf(`@media ${FI_TOUCH_QUERY}`));

    expect(touchBlock).toContain('--fi-touch-target, 44px');
  });
});
