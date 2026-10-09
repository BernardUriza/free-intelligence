'use client';

/**
 * fi-glass · ChatFilePreview — attachment preview (icon, name, size, progress,
 * cancel). Pure presentation driven by props; the upload STATE lives in the app
 * (useChatUpload). Every class is a Tailwind utility the consumer already scans
 * fi-glass's dist for, or a fi-glass primitive: no class that only aurity defines.
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
import { useTouchTargetStyle, withTouchTarget } from './touchTarget';

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
  useTouchTargetStyle();

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
          <Loader2 className="w-5 h-5 text-slate-300 animate-spin" />
        ) : isCompleted ? (
          <CheckCircle className="w-5 h-5 text-emerald-400" />
        ) : isError ? (
          <AlertCircle className="w-5 h-5 text-red-400" />
        ) : (
          <FileIcon className="w-5 h-5 text-slate-300" />
        )}
      </div>

      {/* File Info */}
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-slate-100 truncate" title={file.name}>
          {file.name}
        </p>
        <div className="flex items-center gap-2 text-xs text-slate-400">
          <span>{formatFileSize(file.size)}</span>
          {isUploading && (
            <>
              <span>-</span>
              <span className="text-slate-300">
                {progress < 100 ? `Subiendo... ${progress}%` : 'Completado'}
              </span>
            </>
          )}
          {isAwaitingUser && (
            <>
              <span>-</span>
              <span className="text-slate-300">Elige cómo usarlo</span>
            </>
          )}
          {isProcessing && (
            <>
              <span>-</span>
              <span className="text-slate-300">Procesando...</span>
            </>
          )}
          {isCompleted && (
            <>
              <span>-</span>
              <span className="text-emerald-400">Indexado</span>
            </>
          )}
          {isError && error && (
            <>
              <span>-</span>
              <span className="text-red-400 truncate" title={error}>
                {error}
              </span>
            </>
          )}
        </div>

        {/* Progress Bar */}
        {isUploading && (
          <div className="mt-2 h-1.5 bg-slate-700 rounded-full overflow-hidden">
            <div
              className="h-full rounded-full bg-slate-300 transition-[width] duration-300"
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
          className={withTouchTarget(
            'shrink-0 rounded-lg p-1.5 text-slate-400 transition-colors hover:bg-white/10 hover:text-slate-100',
          )}
          aria-label="Cancelar"
          title="Cancelar"
        >
          <X className="h-4 w-4" />
        </button>
      )}
    </div>
  );
}
