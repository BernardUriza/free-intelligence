/**
 * ChatFilePreview Component
 *
 * Shows file attachment preview before/during upload in chat.
 * Displays: icon, name, size, progress bar, cancel button.
 *
 * Card: FI-UI-FEAT-022
 */
'use client';

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
import { Button } from '@/components/ui/button';

export type UploadStatus =
  | 'selecting'
  | 'uploading'
  | 'pending_instructions'
  | 'processing'
  | 'indexed'
  | 'error';

export interface ChatFilePreviewProps {
  file: File;
  status: UploadStatus;
  progress?: number;        // 0-100 for upload progress
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
  const isProcessing = status === 'processing' || status === 'pending_instructions';

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

      {/* Cancel Button */}
      {!isCompleted && !isProcessing && (
        <Button
          onClick={onCancel}
          variant="ghost"
          size="sm"
          icon={X}
          className="fi-hover-bg"
          aria-label="Cancelar"
          title="Cancelar"
        />
      )}
    </div>
  );
}

export default ChatFilePreview;
