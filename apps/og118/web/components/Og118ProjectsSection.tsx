'use client';

/**
 * Og118ProjectsSection — the Projects affordance in the sidebar (proj-sidebar).
 *
 * A project is a named corpus the agent searches. The owner creates one ("Negocio
 * de mamá"), selects it active, and uploads files to it (proj-uploadui, next).
 * Pure presentation + branding over the useOg118Projects hook — no storage logic
 * here. Reuses the framework touch-target minimum (B3-FIGLASS-MOBILE-2) so the
 * controls are tappable on a phone (the papelería canary is mobile).
 */

import { FI_TOUCH_TARGET_CLASS, useTouchTargetStyle } from 'fi-glass/shell';
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
          {projects.map((p) => {
            const active = p.id === activeProjectId;
            return (
              <div
                key={p.id}
                className={`og-project-item${active ? ' is-active' : ''}`}
                role="button"
                tabIndex={0}
                aria-current={active}
                onClick={() => !disabled && !active && onSelect(p.id)}
                onKeyDown={(e) => {
                  if ((e.key === 'Enter' || e.key === ' ') && !disabled && !active) {
                    e.preventDefault();
                    onSelect(p.id);
                  }
                }}
              >
                <span className="og-project-item-name">{p.name}</span>
                <button
                  className={`${FI_TOUCH_TARGET_CLASS} og-project-item-del`}
                  aria-label="Borrar proyecto"
                  disabled={disabled}
                  onClick={(e) => {
                    e.stopPropagation();
                    if (window.confirm(`¿Borrar "${p.name}"? Solo se borra de este navegador.`)) {
                      onDelete(p.id);
                    }
                  }}
                >
                  ×
                </button>
              </div>
            );
          })}
        </nav>
      )}
    </section>
  );
}
