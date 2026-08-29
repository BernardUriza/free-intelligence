// @vitest-environment jsdom
/**
 * NEXT_PUBLIC_OG118_PROYECTOS — the RENDER half of the switch.
 *
 * Two surfaces, both branches each: the sidebar section (which carries "+ Nuevo",
 * the upload panel and the "Ver todos los proyectos →" link) and the `/projects`
 * route, which a static export still emits and a bookmark can still open.
 *
 * Every OFF assertion is paired with its ON control. "The link is not there"
 * proves nothing on its own — a typo in the query would pass it while the feature
 * shipped in full.
 */

import { describe, it, expect, afterEach, vi } from 'vitest';
import { cleanup, render, screen, waitFor } from '@testing-library/react';

import { Og118ProjectsSection } from '../projects';
import type { Og118Project } from '@/lib/useOg118Projects';
import ProjectsRoute from '@/app/projects/page';

const PROJECTS: Og118Project[] = [
  { id: 'p1', name: 'Negocio de mamá' } as Og118Project,
  { id: 'p2', name: 'Tareas escuela' } as Og118Project,
];

function section(activeProjectId: string | null = 'p1') {
  return render(
    <Og118ProjectsSection
      projects={PROJECTS}
      activeProjectId={activeProjectId}
      onCreate={vi.fn()}
      onSelect={vi.fn()}
      onDelete={vi.fn()}
      onUpload={vi.fn()}
    />,
  );
}

afterEach(() => {
  cleanup();
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

describe('Og118ProjectsSection under the flag', () => {
  it('OFF: mounts nothing at all — no rows, no "+ Nuevo", no upload, no page link', () => {
    const { container } = section();
    expect(container).toBeEmptyDOMElement();
    expect(screen.queryByRole('button', { name: 'Nuevo proyecto' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Negocio de mamá' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /subir archivo/i })).not.toBeInTheDocument();
    expect(screen.queryByText(/ver todos los proyectos/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/crea un proyecto/i)).not.toBeInTheDocument();
  });

  it('ON: the control — the same props render the whole surface', () => {
    vi.stubEnv('NEXT_PUBLIC_OG118_PROYECTOS', '1');
    const { container } = section();
    expect(container).not.toBeEmptyDOMElement();
    expect(screen.getByRole('button', { name: 'Nuevo proyecto' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Negocio de mamá' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /subir archivo/i })).toBeInTheDocument();
    expect(screen.getByText(/ver todos los proyectos/i)).toBeInTheDocument();
  });
});

describe('/projects route under the flag', () => {
  it('OFF: renders the unavailable notice and fires no request', () => {
    const fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);
    render(<ProjectsRoute />);
    expect(screen.getByText(/proyectos no está disponible/i)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /volver al chat/i })).toHaveAttribute('href', '/');
    // Nothing from the real page mounted: no index header, no create affordance.
    expect(screen.queryByRole('button', { name: /nuevo proyecto/i })).not.toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('ON: the control — the real page mounts and hydrates from GET /projects', async () => {
    vi.stubEnv('NEXT_PUBLIC_OG118_PROYECTOS', '1');
    const fetchMock = vi
      .fn()
      .mockResolvedValue({ ok: true, json: async () => ({ projects: [] }) });
    vi.stubGlobal('fetch', fetchMock);
    render(<ProjectsRoute />);
    expect(screen.queryByText(/proyectos no está disponible/i)).not.toBeInTheDocument();
    // RTL's waitFor (not vi's) so the post-fetch state updates settle inside act().
    await waitFor(() => expect(fetchMock).toHaveBeenCalled());
    expect(String(fetchMock.mock.calls[0][0])).toMatch(/\/projects$/);
  });
});
