'use client';

/**
 * Og118ProjectCreateRow — the inline create-project input (qa-prompt-native).
 *
 * Renders the SAME machine + input styling as the rename (fi-glass
 * useInlineRename / FI_RESOURCE_RENAME_INPUT_CLASS): Enter creates, Escape
 * cancels, an empty draft closes silently. The machine lives in the
 * orchestrator because the "+ Nuevo" trigger (section actionSlot) and the
 * empty-state suppression share its `editing` state; this row only renders it.
 */

import { useId } from 'react';
import { FI_RESOURCE_RENAME_INPUT_CLASS } from 'fi-glass/agent';
import type { InlineRename } from 'fi-glass/agent';

export interface Og118ProjectCreateRowProps {
  create: InlineRename;
}

export function Og118ProjectCreateRow({ create }: Og118ProjectCreateRowProps) {
  const inputId = useId();
  if (!create.editing) return null;
  return (
    <div className="og-project-create">
      <input
        id={inputId}
        name="project-name"
        className={FI_RESOURCE_RENAME_INPUT_CLASS}
        aria-label="Nombre del proyecto"
        placeholder='p. ej. "Negocio de mamá"'
        {...create.inputProps}
      />
    </div>
  );
}
