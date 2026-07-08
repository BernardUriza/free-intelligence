'use client';

/**
 * Og118ProjectUploadPanel — the upload affordance for the ACTIVE project
 * (PROJECTS-DOCS-E2E). Button + fi-glass ChatFilePreview (status/progress/
 * error) + the indexed-chunks confirmation. State comes from
 * useOg118ProjectUpload via the orchestrator; this panel owns only the copy
 * and the composition.
 */

import { ChatFilePreview, FI_TOUCH_TARGET_CLASS } from 'fi-glass/shell';
import type { UploadStatus } from 'fi-glass/shell';

export interface Og118ProjectUploadPanelProps {
  activeProjectId: string;
  disabled: boolean;
  uploadFile?: File | null;
  uploadStatus?: UploadStatus;
  uploadProgress?: number;
  uploadError?: string | null;
  uploadChunks?: number | null;
  onUpload: (projectId: string) => void;
  onCancelUpload?: () => void;
}

export function Og118ProjectUploadPanel({
  activeProjectId,
  disabled,
  uploadFile,
  uploadStatus,
  uploadProgress,
  uploadError,
  uploadChunks,
  onUpload,
  onCancelUpload,
}: Og118ProjectUploadPanelProps) {
  return (
    <div className="og-project-upload">
      <button
        className={`${FI_TOUCH_TARGET_CLASS} og-project-upload-btn`}
        onClick={() => onUpload(activeProjectId)}
        disabled={disabled || uploadStatus === 'uploading'}
        aria-label="Subir archivo al proyecto"
      >
        + Subir archivo (.txt / .md)
      </button>
      {uploadFile && uploadStatus && (
        <ChatFilePreview
          file={uploadFile}
          status={uploadStatus}
          progress={uploadProgress}
          error={uploadError ?? undefined}
          onCancel={() => onCancelUpload?.()}
        />
      )}
      {uploadStatus === 'indexed' && typeof uploadChunks === 'number' && (
        <p className="og-project-upload-done">
          Indexado en el proyecto · {uploadChunks} fragmento{uploadChunks === 1 ? '' : 's'}
        </p>
      )}
    </div>
  );
}
