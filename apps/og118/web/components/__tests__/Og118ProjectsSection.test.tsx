/**
 * Tests for Og118ProjectsSection after it adopted the shared fi-glass
 * `AgentSidebarItem` primitive (B3-FIGLASS-SHELL-PRIMITIVES-1B).
 *
 * The hand-written `og-project-item` twin is gone; the rows are now the same
 * selectable-resource primitive the conversation list uses. These assert the
 * consumer still owns the meaning: project labels, selection, and the
 * confirm-gated delete behave exactly as before through the primitive's slots.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Og118ProjectsSection } from '../Og118ProjectsSection';
import type { Og118Project } from '../../lib/useOg118Projects';

const projects: Og118Project[] = [
  { id: 'p1', name: 'Negocio de mamá' } as Og118Project,
  { id: 'p2', name: 'Tareas escuela' } as Og118Project,
];

describe('Og118ProjectsSection (1B — shared sidebar item)', () => {
  it('renders the empty-state copy when there are no projects', () => {
    render(
      <Og118ProjectsSection
        projects={[]}
        activeProjectId={null}
        onCreate={vi.fn()}
        onSelect={vi.fn()}
        onDelete={vi.fn()}
      />,
    );
    expect(screen.getByText(/crea un proyecto/i)).toBeInTheDocument();
  });

  it('renders one selectable row per project, labeled by name', () => {
    render(
      <Og118ProjectsSection
        projects={projects}
        activeProjectId={null}
        onCreate={vi.fn()}
        onSelect={vi.fn()}
        onDelete={vi.fn()}
      />,
    );
    expect(screen.getByRole('button', { name: 'Negocio de mamá' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Tareas escuela' })).toBeInTheDocument();
  });

  it('marks the active project with aria-current and does not re-select it on click', async () => {
    const onSelect = vi.fn();
    render(
      <Og118ProjectsSection
        projects={projects}
        activeProjectId="p1"
        onCreate={vi.fn()}
        onSelect={onSelect}
        onDelete={vi.fn()}
      />,
    );
    const activeRow = screen.getByRole('button', { name: 'Negocio de mamá' });
    expect(activeRow).toHaveAttribute('aria-current', 'true');
    await userEvent.click(activeRow);
    expect(onSelect).not.toHaveBeenCalled();
  });

  it('fires onSelect when a non-active project row is clicked', async () => {
    const onSelect = vi.fn();
    render(
      <Og118ProjectsSection
        projects={projects}
        activeProjectId="p1"
        onCreate={vi.fn()}
        onSelect={onSelect}
        onDelete={vi.fn()}
      />,
    );
    await userEvent.click(screen.getByRole('button', { name: 'Tareas escuela' }));
    expect(onSelect).toHaveBeenCalledWith('p2');
  });
});

describe('Og118ProjectsSection delete (confirm-gated)', () => {
  beforeEach(() => {
    vi.spyOn(window, 'confirm');
  });
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('deletes only when the confirm is accepted', async () => {
    (window.confirm as ReturnType<typeof vi.fn>).mockReturnValue(true);
    const onDelete = vi.fn();
    render(
      <Og118ProjectsSection
        projects={projects}
        activeProjectId={null}
        onCreate={vi.fn()}
        onSelect={vi.fn()}
        onDelete={onDelete}
      />,
    );
    const delButtons = screen.getAllByRole('button', { name: 'Borrar proyecto' });
    await userEvent.click(delButtons[0]);
    expect(onDelete).toHaveBeenCalledWith('p1');
  });

  it('does NOT delete when the confirm is dismissed', async () => {
    (window.confirm as ReturnType<typeof vi.fn>).mockReturnValue(false);
    const onDelete = vi.fn();
    render(
      <Og118ProjectsSection
        projects={projects}
        activeProjectId={null}
        onCreate={vi.fn()}
        onSelect={vi.fn()}
        onDelete={onDelete}
      />,
    );
    await userEvent.click(screen.getAllByRole('button', { name: 'Borrar proyecto' })[0]);
    expect(onDelete).not.toHaveBeenCalled();
  });

  it('does not bubble a delete click up to row selection', async () => {
    (window.confirm as ReturnType<typeof vi.fn>).mockReturnValue(true);
    const onSelect = vi.fn();
    render(
      <Og118ProjectsSection
        projects={projects}
        activeProjectId={null}
        onCreate={vi.fn()}
        onSelect={onSelect}
        onDelete={vi.fn()}
      />,
    );
    await userEvent.click(screen.getAllByRole('button', { name: 'Borrar proyecto' })[0]);
    expect(onSelect).not.toHaveBeenCalled();
  });
});

// PROJECTS-DOCS-E2E: the upload affordance is scoped to the ACTIVE project and
// reuses the fi-glass ChatFilePreview. The section stays dumb — it owns the
// meaning (which project, the Spanish copy), the transport lives in the hook.
describe('Og118ProjectsSection upload (PROJECTS-DOCS-E2E)', () => {
  it('shows NO upload button without an active project', () => {
    render(
      <Og118ProjectsSection
        projects={projects}
        activeProjectId={null}
        onCreate={vi.fn()}
        onSelect={vi.fn()}
        onDelete={vi.fn()}
        onUpload={vi.fn()}
      />,
    );
    expect(screen.queryByRole('button', { name: /subir archivo/i })).not.toBeInTheDocument();
  });

  it('shows NO upload button when onUpload is absent (capability off)', () => {
    render(
      <Og118ProjectsSection
        projects={projects}
        activeProjectId="p1"
        onCreate={vi.fn()}
        onSelect={vi.fn()}
        onDelete={vi.fn()}
      />,
    );
    expect(screen.queryByRole('button', { name: /subir archivo/i })).not.toBeInTheDocument();
  });

  it('fires onUpload with the ACTIVE project id', async () => {
    const onUpload = vi.fn();
    render(
      <Og118ProjectsSection
        projects={projects}
        activeProjectId="p2"
        onCreate={vi.fn()}
        onSelect={vi.fn()}
        onDelete={vi.fn()}
        onUpload={onUpload}
      />,
    );
    await userEvent.click(screen.getByRole('button', { name: /subir archivo al proyecto/i }));
    expect(onUpload).toHaveBeenCalledWith('p2');
  });

  it('renders the file preview while uploading and surfaces the error', () => {
    render(
      <Og118ProjectsSection
        projects={projects}
        activeProjectId="p1"
        onCreate={vi.fn()}
        onSelect={vi.fn()}
        onDelete={vi.fn()}
        onUpload={vi.fn()}
        onCancelUpload={vi.fn()}
        uploadFile={new File(['x'], 'doc.pdf', { type: 'application/pdf' })}
        uploadStatus="error"
        uploadError="Solo archivos de texto (.txt o .md)."
      />,
    );
    expect(screen.getByText('doc.pdf')).toBeInTheDocument();
    expect(screen.getByText(/solo archivos de texto/i)).toBeInTheDocument();
  });

  it('confirms the indexed chunk count on success', () => {
    render(
      <Og118ProjectsSection
        projects={projects}
        activeProjectId="p1"
        onCreate={vi.fn()}
        onSelect={vi.fn()}
        onDelete={vi.fn()}
        onUpload={vi.fn()}
        uploadFile={new File(['hola'], 'notas.txt', { type: 'text/plain' })}
        uploadStatus="indexed"
        uploadChunks={3}
      />,
    );
    expect(screen.getByText(/3 fragmentos/i)).toBeInTheDocument();
  });
});
