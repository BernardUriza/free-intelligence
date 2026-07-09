'use client';

/**
 * Og118ProjectsSection — the Projects affordance in the sidebar (proj-sidebar).
 *
 * A project is a named corpus the agent searches. The owner creates one ("Negocio
 * de mamá"), selects it active, and uploads text files to its corpus
 * (PROJECTS-DOCS-E2E). Pure orchestrator: the section skeleton is fi-glass
 * `AgentSidebarSection` (B3-FIGLASS-SHELL-PRIMITIVES-1C); the organs live next
 * door — Og118ProjectCreateRow (inline create, qa-prompt-native),
 * Og118ProjectRow (row + confirm-gated delete), Og118ProjectUploadPanel
 * (upload + preview + indexed feedback). This file owns only the wiring and
 * the create machine (its `editing` state is shared by the "+ Nuevo" trigger,
 * the create row, and the empty-state suppression). No storage logic here.
 */

import { FI_TOUCH_TARGET_CLASS, useTouchTargetStyle } from 'fi-glass/shell';
import type { UploadStatus } from 'fi-glass/shell';
import { AgentSidebarSection, useInlineRename, useSidebarItemStyle } from 'fi-glass/agent';
import type { Og118Project } from '../../lib/useOg118Projects';
import { Og118ProjectCreateRow } from './Og118ProjectCreateRow';
import { Og118ProjectRow } from './Og118ProjectRow';
import { Og118ProjectUploadPanel } from './Og118ProjectUploadPanel';

export interface Og118ProjectsSectionProps {
  projects: Og118Project[];
  activeProjectId: string | null;
  onCreate: (name: string) => void;
  onSelect: (id: string) => void;
  onDelete: (id: string) => void;
  /** Disable mutations while a turn streams. */
  disabled?: boolean;
  // ---- Upload (state from useOg118ProjectUpload; scoped to the active project) ----
  // Absent onUpload → no upload affordance (the section degrades to list-only).
  uploadFile?: File | null;
  uploadStatus?: UploadStatus;
  uploadProgress?: number;
  uploadError?: string | null;
  uploadChunks?: number | null;
  onUpload?: (projectId: string) => void;
  onCancelUpload?: () => void;
}

export function Og118ProjectsSection({
  projects,
  activeProjectId,
  onCreate,
  onSelect,
  onDelete,
  disabled = false,
  uploadFile,
  uploadStatus,
  uploadProgress,
  uploadError,
  uploadChunks,
  onUpload,
  onCancelUpload,
}: Og118ProjectsSectionProps) {
  useTouchTargetStyle();
  // qa-prompt-native: creation shares the SAME inline-edit machine + input
  // styling as the rename (fi-glass useInlineRename / EditableResourceItem) —
  // Enter creates, Escape cancels, an empty draft closes silently.
  useSidebarItemStyle();
  const create = useInlineRename(
    '',
    (name) => {
      if (name.trim()) onCreate(name.trim());
    },
    { maxLength: 80, emptyPolicy: 'keep' },
  );

  return (
    <AgentSidebarSection
      className="og-projects"
      ariaLabel="Proyectos"
      title="Proyectos"
      variant="card"
      scrollBehavior="content"
      count={projects.length}
      actionSlot={
        <button
          className={`${FI_TOUCH_TARGET_CLASS} og-projects-new`}
          onClick={create.start}
          disabled={disabled}
          aria-label="Nuevo proyecto"
        >
          + Nuevo
        </button>
      }
      emptyState={
        create.editing ? undefined : (
          <p className="og-projects-empty">
            Crea un proyecto, súbele archivos y pregúntale a og118 sobre ellos.
          </p>
        )
      }
      footerSlot={
        activeProjectId && onUpload ? (
          <Og118ProjectUploadPanel
            activeProjectId={activeProjectId}
            disabled={disabled}
            uploadFile={uploadFile}
            uploadStatus={uploadStatus}
            uploadProgress={uploadProgress}
            uploadError={uploadError}
            uploadChunks={uploadChunks}
            onUpload={onUpload}
            onCancelUpload={onCancelUpload}
          />
        ) : undefined
      }
    >
      <nav className="og-projects-list">
        <Og118ProjectCreateRow create={create} />
        {projects.map((p) => (
          <Og118ProjectRow
            key={p.id}
            project={p}
            selected={p.id === activeProjectId}
            disabled={disabled}
            onSelect={onSelect}
            onDelete={onDelete}
          />
        ))}
      </nav>
    </AgentSidebarSection>
  );
}
