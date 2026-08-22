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
