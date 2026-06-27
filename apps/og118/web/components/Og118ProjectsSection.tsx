'use client';

/**
 * Og118ProjectsSection — the Projects affordance in the sidebar (proj-sidebar).
 *
 * A project is a named corpus the agent searches. The owner creates one ("Negocio
 * de mamá"), selects it active, and uploads files to it (proj-uploadui, next).
 * The rows are fi-glass `AgentSidebarItem` (B3-FIGLASS-SHELL-PRIMITIVES-1B) — the
 * same selectable-resource-row primitive the conversation list adopted in 1A, so
 * the `og-project-item`/`og-chat-item` structural twin is now a single shared
 * skeleton. This consumer owns ONLY the meaning: a Project, the Spanish copy, the
 * delete confirm, the create prompt. No storage logic here.
 */

import { FI_TOUCH_TARGET_CLASS, useTouchTargetStyle } from 'fi-glass/shell';
import { AgentSidebarItem, DestructiveActionSlot } from 'fi-glass/agent';
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
    <section className="og-projects">
      <div className="og-projects-head">
        <span className="og-projects-title">Proyectos</span>
        <button
          className={`${FI_TOUCH_TARGET_CLASS} og-projects-new`}
          onClick={handleNew}
          disabled={disabled}
          aria-label="Nuevo proyecto"
        >
          + Nuevo
        </button>
      </div>

      {projects.length === 0 ? (
        <p className="og-projects-empty">
          Crea un proyecto, súbele archivos y pregúntale a og118 sobre ellos.
        </p>
      ) : (
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
                      window.confirm(`¿Borrar "${p.name}"? Solo se borra de este navegador.`)
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
      )}
    </section>
  );
}
