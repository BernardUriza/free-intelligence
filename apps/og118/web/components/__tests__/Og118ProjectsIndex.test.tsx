// @vitest-environment jsdom
/**
 * The Projects index page (FIGLASS-PROJECTS-PAGE-1, §A).
 *
 * What is pinned here is og118's half — the sort, the copy, the accent-tolerant
 * search — not fi-glass's grid, which has its own contract tests.
 *
 * The empty state has TWO meanings and they must not be confused: "you have no
 * projects" is an invitation, "nothing matched your search" is a dead end. One
 * message for both would tell someone with twenty projects that they have none.
 */

import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Og118ProjectsIndex } from '../projects/Og118ProjectsIndex';
import type { Og118Project } from '@/lib/useOg118Projects';

afterEach(cleanup);

const NOW = Date.parse('2026-08-22T12:00:00Z');

function project(over: Partial<Og118Project> & { id: string; name: string }): Og118Project {
  return {
    description: '',
    instructions: '',
    createdAt: '2026-08-01T12:00:00Z',
    updatedAt: '2026-08-01T12:00:00Z',
    ...over,
  };
}

const PROJECTS: Og118Project[] = [
  project({
    id: 'p1',
    name: 'Papelería',
    description: 'precios y proveedores',
    updatedAt: '2026-08-21T12:00:00Z',
  }),
  project({ id: 'p2', name: 'Contabilidad', updatedAt: '2026-08-10T12:00:00Z' }),
];

function renderIndex(over: Partial<React.ComponentProps<typeof Og118ProjectsIndex>> = {}) {
  return render(
    <Og118ProjectsIndex
      projects={PROJECTS}
      ready
      onOpen={vi.fn()}
      onCreate={vi.fn()}
      now={NOW}
      {...over}
    />,
  );
}

describe('Og118ProjectsIndex', () => {
  it('sorts by last updated first', () => {
    renderIndex();

    const titles = screen.getAllByRole('listitem').map((li) => li.textContent);
    expect(titles[0]).toContain('Papelería');
    expect(titles[1]).toContain('Contabilidad');
  });

  it('renders the description and a relative "Actualizado" on the card', () => {
    renderIndex();

    expect(screen.getByText('precios y proveedores')).toBeTruthy();
    expect(screen.getByText(/Actualizado ayer/)).toBeTruthy();
  });

  it('finds an accented project from an unaccented query', async () => {
    renderIndex();

    await userEvent.type(screen.getByRole('searchbox'), 'papeleria');

    expect(screen.getAllByRole('listitem')).toHaveLength(1);
    expect(screen.getByText('Papelería')).toBeTruthy();
  });

  it('distinguishes "no tienes proyectos" from "nada coincide"', async () => {
    const { unmount } = renderIndex();
    await userEvent.type(screen.getByRole('searchbox'), 'zzz');
    expect(screen.getByText(/Ningún proyecto coincide/)).toBeTruthy();
    unmount();

    renderIndex({ projects: [] });
    expect(screen.getByText(/Todavía no tienes proyectos/)).toBeTruthy();
  });

  it('says it is loading instead of claiming the account has no projects', () => {
    renderIndex({ ready: false, projects: [] });

    expect(screen.getByText(/Cargando tus proyectos/)).toBeTruthy();
    expect(screen.queryByText(/Todavía no tienes proyectos/)).toBeNull();
  });

  it('opens a project by its id', async () => {
    const onOpen = vi.fn();
    renderIndex({ onOpen });

    await userEvent.click(screen.getByRole('button', { name: /Papelería/ }));

    expect(onOpen).toHaveBeenCalledWith('p1');
  });

  it('switching the sort to name reorders and relabels the meta', async () => {
    renderIndex();

    await userEvent.selectOptions(screen.getByLabelText('Ordenar proyectos'), 'created');

    expect(screen.getAllByText(/^Creado /)).toHaveLength(2);
  });

  it('a project with no description renders no empty subtitle line', () => {
    const { container } = renderIndex({ projects: [PROJECTS[1]] });

    expect(container.querySelector('.fi-resource-card-desc')).toBeNull();
  });
});
