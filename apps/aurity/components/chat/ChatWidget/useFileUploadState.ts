/**
 * useFileUploadState Hook
 *
 * Wraps useChatUpload with simplified interface.
 * SOLID: Single Responsibility - only file upload handling.
 */

import { useCallback } from 'react';
import { useChatUpload } from '@aurity-standalone/hooks/useChatUpload';
import type { PersonaType } from '../ChatToolbar';

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
  } = useChatUpload({
    persona,
    userId,
    onUploadComplete: (doc) => {
      console.log('[FileUpload] Complete:', doc.doc_id);
    },
    onIndexed: (doc) => {
      console.log('[FileUpload] Indexed:', doc.doc_id, doc.chunks_count, 'chunks');
      setTimeout(reset, 3000);
    },
    onError: (error) => {
      console.error('[FileUpload] Error:', error);
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
    handleDragOver,
    handleDrop,
  };
}
