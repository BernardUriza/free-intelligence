'use client';

/**
 * Og118ProjectRow — one project in the sidebar list: the shared fi-glass
 * AgentSidebarItem (B3-FIGLASS-SHELL-PRIMITIVES-1B) plus the confirm-gated
 * delete. The consumer meaning lives here (Spanish copy, the confirm text);
 * the row anatomy is the framework's.
 */

import { AgentSidebarItem, DestructiveActionSlot } from 'fi-glass/agent';
import type { Og118Project } from '../../lib/useOg118Projects';

export interface Og118ProjectRowProps {
  project: Og118Project;
  selected: boolean;
  disabled: boolean;
  onSelect: (id: string) => void;
  onDelete: (id: string) => void;
}

export function Og118ProjectRow({
  project,
  selected,
  disabled,
  onSelect,
  onDelete,
}: Og118ProjectRowProps) {
  return (
    <AgentSidebarItem
      title={project.name}
      selected={selected}
      onSelect={() => onSelect(project.id)}
      disabled={disabled}
      ariaLabel={project.name}
      actions={
        <DestructiveActionSlot
          label="Borrar proyecto"
          disabled={disabled}
          onActivate={() => {
            if (
              window.confirm(`¿Borrar "${project.name}"? Se borra de tu cuenta y sus documentos.`)
            ) {
              onDelete(project.id);
            }
          }}
        >
          ×
        </DestructiveActionSlot>
      }
    />
  );
}
