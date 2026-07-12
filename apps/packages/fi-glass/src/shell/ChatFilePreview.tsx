'use client';

/**
 * fi-glass · ChatFilePreview — attachment preview (icon, name, size, progress,
 * cancel). Pure presentation driven by props; the upload STATE lives in the app
 * (useChatUpload). The only app coupling — `@/components/ui/button` for the
 * cancel X — is inlined as `<button class="fi-btn-ghost fi-btn-sm …">` (the exact
 * class output of `<Button variant="ghost" size="sm" icon={X}>`), render-diff safe.
 */

import {
  FileText,
  FileCode,
  Image as ImageIcon,
  File,
  X,
  Loader2,
  CheckCircle,
  AlertCircle,
} from 'lucide-react';
import type { UploadStatus } from './types';

export interface ChatFilePreviewProps {
  file: File;
  status: UploadStatus;
  progress?: number;
  error?: string;
  onCancel: () => void;
}

const FILE_ICONS: Record<string, typeof FileText> = {
  'application/pdf': FileText,
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': FileText,
  'application/msword': FileText,
  'text/plain': File,
  'text/markdown': FileCode,
  'image/png': ImageIcon,
  'image/jpeg': ImageIcon,
  'image/jpg': ImageIcon,
};

function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

function getFileIcon(file: File) {
  return FILE_ICONS[file.type] || File;
}

export function ChatFilePreview({
  file,
  status,
  progress = 0,
  error,
  onCancel,
}: ChatFilePreviewProps) {
  const FileIcon = getFileIcon(file);

  const isCompleted = status === 'indexed';
  const isError = status === 'error';
  const isUploading = status === 'uploading';
  // `pending_instructions` is NOT processing: nothing is running, the flow is
  // WAITING FOR THE USER to say how the document should be used. Calling it
  // "Procesando…" spun a loader forever AND hid the cancel button (see below),
  // so an upload that stalled here could not even be dismissed.
  const isProcessing = status === 'processing';
  const isAwaitingUser = status === 'pending_instructions';

  return (
    <div className={`
      flex items-center gap-3 p-3 rounded-xl border
      ${isError
        ? 'bg-red-900/20 border-red-700/50'
        : isCompleted
          ? 'bg-emerald-900/20 border-emerald-700/50'
          : 'bg-slate-800/80 border-slate-700/50'
      }
      transition-colors duration-200
    `}>
      {/* File Icon */}
      <div className={`
        p-2 rounded-lg
        ${isError
          ? 'bg-red-900/50'
          : isCompleted
            ? 'bg-emerald-900/50'
            : 'bg-slate-700'
        }
      `}>
        {isProcessing ? (
          <Loader2 className="w-5 h-5 fi-text-primary animate-spin" />
        ) : isCompleted ? (
          <CheckCircle className="w-5 h-5 fi-text-success" />
        ) : isError ? (
          <AlertCircle className="w-5 h-5 fi-text-error" />
        ) : (
          <FileIcon className="w-5 h-5 fi-text" />
        )}
      </div>

      {/* File Info */}
      <div className="flex-1 min-w-0">
        <p className="fi-title-sm-medium truncate" title={file.name}>
          {file.name}
        </p>
        <div className="flex items-center gap-2 fi-text-xs">
          <span>{formatFileSize(file.size)}</span>
          {isUploading && (
            <>
              <span>-</span>
              <span className="fi-text-primary">
                {progress < 100 ? `Subiendo... ${progress}%` : 'Completado'}
              </span>
            </>
          )}
          {isAwaitingUser && (
            <>
              <span>-</span>
              <span className="fi-text-primary">Elige cómo usarlo</span>
            </>
          )}
          {isProcessing && (
            <>
              <span>-</span>
              <span className="fi-text-primary">Procesando...</span>
            </>
          )}
          {isCompleted && (
            <>
              <span>-</span>
              <span className="chat-file-status-indexed">Indexado</span>
            </>
          )}
          {isError && error && (
            <>
              <span>-</span>
              <span className="fi-text-error truncate" title={error}>
                {error}
              </span>
            </>
          )}
        </div>

        {/* Progress Bar */}
        {isUploading && (
          <div className="mt-2 h-1.5 bg-slate-700 rounded-full overflow-hidden">
            <div
              className="fi-progress-bar duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
        )}
      </div>

      {/* Cancel Button — available whenever the user could be stuck, which
          includes waiting-for-instructions (it did NOT before). */}
      {!isCompleted && !isProcessing && (
        <button
          type="button"
          onClick={onCancel}
          className="fi-btn-ghost fi-btn-sm fi-hover-bg"
          aria-label="Cancelar"
          title="Cancelar"
        >
          <X className="h-4 w-4" />
        </button>
      )}
    </div>
  );
}
