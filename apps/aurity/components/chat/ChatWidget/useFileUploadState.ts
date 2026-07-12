/**
 * useFileUploadState Hook
 *
 * Wraps useChatUpload with simplified interface.
 * SOLID: Single Responsibility - only file upload handling.
 */

import { useCallback } from 'react';
import { useChatUpload } from '@aurity-standalone/hooks/useChatUpload';
import type { PersonaType } from 'fi-glass/shell';
import { createLogger } from '@/lib/internal/logger';

const log = createLogger('FileUpload');

export interface UseFileUploadStateOptions {
  persona: PersonaType;
  userId?: string;
}

export type UploadStatus =
  | 'selecting'
  | 'uploading'
  | 'pending_instructions'
  | 'processing'
  | 'indexed'
  | 'error';

export interface UseFileUploadStateReturn {
  file: File | null;
  status: UploadStatus;
  isActive: boolean;
  openPicker: () => void;
  handleFile: (file: File) => void;
  cancel: () => void;
  /**
   * Answer "how should the persona use this document?" — the step that ACTUALLY
   * starts the indexing. `useChatUpload` has always exported it and this wrapper
   * never surfaced it, so nothing in the app could call it: every upload parked
   * in `pending_instructions` and never indexed.
   */
  setInstructions: (instructions: string) => Promise<void>;
  /** True while the upload waits for that answer (renders the prompt). */
  isPending: boolean;
  handleDragOver: (e: React.DragEvent) => void;
  handleDrop: (e: React.DragEvent) => void;
}

export function useFileUploadState({
  persona,
  userId,
}: UseFileUploadStateOptions): UseFileUploadStateReturn {
  const {
    file,
    status,
    isActive,
    openFilePicker,
    handleFileSelect,
    cancel,
    reset,
    setInstructions,
    isPending,
  } = useChatUpload({
    persona,
    userId,
    onUploadComplete: () => {},
    onIndexed: () => {
      setTimeout(reset, 3000);
    },
    onError: (error) => {
      log.error('Upload failed', { error: String(error) });
    },
  });

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      handleFileSelect(files[0]);
    }
  }, [handleFileSelect]);

  return {
    file,
    status: status as UploadStatus,
    isActive,
    openPicker: openFilePicker,
    handleFile: handleFileSelect,
    cancel,
    setInstructions,
    isPending,
    handleDragOver,
    handleDrop,
  };
}
