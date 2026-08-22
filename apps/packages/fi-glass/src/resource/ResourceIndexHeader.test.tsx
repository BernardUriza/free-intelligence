// @vitest-environment jsdom
/**
 * The index page header (FIGLASS-PROJECTS-PAGE-1).
 *
 * It renders no button of its own — both controls arrive as slots — which is how
 * it stays incapable of acquiring an opinion about what the resource is called.
 */

import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import { ResourceIndexHeader } from './ResourceIndexHeader';

afterEach(cleanup);

describe('ResourceIndexHeader', () => {
  it('promotes a string title to the page heading', () => {
    render(<ResourceIndexHeader title="Proyectos" />);

    expect(screen.getByRole('heading', { level: 1, name: 'Proyectos' })).toBeTruthy();
  });

  it('uses a node title as-is', () => {
    const { container } = render(<ResourceIndexHeader title={<span>marca</span>} />);

    expect(container.querySelector('h1')).toBeNull();
    expect(screen.getByText('marca')).toBeTruthy();
  });

  it('renders the sort and action slots together', () => {
    render(
      <ResourceIndexHeader
        title="Proyectos"
        sortSlot={<button type="button">Ordenar</button>}
        actionSlot={<button type="button">Nuevo</button>}
      />,
    );

    expect(screen.getByRole('button', { name: 'Ordenar' })).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Nuevo' })).toBeTruthy();
  });

  it('renders no actions container when neither slot was given', () => {
    const { container } = render(<ResourceIndexHeader title="Proyectos" />);

    expect(container.querySelector('.fi-resource-index-actions')).toBeNull();
  });
});
