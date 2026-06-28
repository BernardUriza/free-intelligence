'use client';

/**
 * Og118ProjectsSection — the Projects affordance in the sidebar (proj-sidebar).
 *
 * A project is a named corpus the agent searches. The owner creates one ("Negocio
 * de mamá"), selects it active, and uploads files to it (proj-uploadui, next).
 * The section is fi-glass `AgentSidebarSection` (B3-FIGLASS-SHELL-PRIMITIVES-1C) —
 * the header + count→empty gate the conversation rail shares — and the rows are
 * fi-glass `AgentSidebarItem` (1B), so both the `og-project-item`/`og-chat-item`
 * row twin AND the `og-projects-head`/`og-sidebar-head` header twin are now single
 * shared skeletons. This consumer owns ONLY the meaning: a Project, the Spanish
 * copy, the delete confirm, the create prompt. No storage logic here.
 */

import { FI_TOUCH_TARGET_CLASS, useTouchTargetStyle } from 'fi-glass/shell';
import { AgentSidebarItem, AgentSidebarSection, DestructiveActionSlot } from 'fi-glass/agent';
import type { Og118Project } from '../lib/useOg118Projects';

export interface Og118ProjectsSectionProps {
  projects: Og118Project[];
  activeProjectId: string | null;
  onCreate: (name: string) => void;
  onSelect: (id: string) => void;
  onDelete: (id: string) => void;
  /** Disable mutations while a turn streams. */
  disabled?: boolean;
}

export function Og118ProjectsSection({
  projects,
  activeProjectId,
  onCreate,
  onSelect,
  onDelete,
  disabled = false,
}: Og118ProjectsSectionProps) {
  useTouchTargetStyle();

  const handleNew = () => {
    const name = window.prompt('Nombre del proyecto (p. ej. "Negocio de mamá")');
    if (name && name.trim()) onCreate(name.trim());
  };

  return (
    <AgentSidebarSection
      className="og-projects"
      ariaLabel="Proyectos"
      title="Proyectos"
      count={projects.length}
      actionSlot={
        <button
          className={`${FI_TOUCH_TARGET_CLASS} og-projects-new`}
          onClick={handleNew}
          disabled={disabled}
          aria-label="Nuevo proyecto"
        >
          + Nuevo
        </button>
      }
      emptyState={
        <p className="og-projects-empty">
          Crea un proyecto, súbele archivos y pregúntale a og118 sobre ellos.
        </p>
      }
    >
      <nav className="og-projects-list">
        {projects.map((p) => (
          <AgentSidebarItem
            key={p.id}
            title={p.name}
            selected={p.id === activeProjectId}
            onSelect={() => onSelect(p.id)}
            disabled={disabled}
            ariaLabel={p.name}
            actions={
              <DestructiveActionSlot
                label="Borrar proyecto"
                disabled={disabled}
                onActivate={() => {
                  if (
                    window.confirm(`¿Borrar "${p.name}"? Se borra de tu cuenta y sus documentos.`)
                  ) {
                    onDelete(p.id);
                  }
                }}
              >
                ×
              </DestructiveActionSlot>
            }
          />
        ))}
      </nav>
    </AgentSidebarSection>
  );
}
