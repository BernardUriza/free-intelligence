/**
 * useChatUpload Hook
 *
 * Manages the document upload flow within the chat widget:
 * 1. File selection/validation
 * 2. Upload to backend
 * 3. Wait for user instructions
 * 4. Update document with instructions
 * 5. Monitor indexing status
 *
 * Card: FI-UI-FEAT-022
 */
'use client';

import { useState, useCallback, useRef } from 'react';
import { uploadDocument, updateDocument } from '@/lib/api/knowledge';
import { ROUTES } from '@/lib/api/routes';
import type { DocumentMetadata } from '@aurity-standalone/types/knowledge';
import { createLogger } from '@/lib/internal/logger';

const log = createLogger('ChatUpload');

export type UploadStatus =
  | 'idle'
  | 'selecting'
  | 'uploading'
  | 'pending_instructions'
  | 'updating'
  | 'processing'
  | 'indexed'
  | 'error';

export interface ChatUploadState {
  file: File | null;
  status: UploadStatus;
  progress: number;
  error: string | null;
  docId: string | null;
  documentMeta: DocumentMetadata | null;
}

export interface UseChatUploadOptions {
  /** Current persona for assignment */
  persona: string;
  /** User ID for upload tracking */
  userId?: string;
  /** Max file size in MB */
  maxSizeMB?: number;
  /** Allowed mime types */
  allowedTypes?: string[];
  /** Callback when upload completes */
  onUploadComplete?: (doc: DocumentMetadata) => void;
  /** Callback when document is indexed */
  onIndexed?: (doc: DocumentMetadata) => void;
  /** Callback for errors */
  onError?: (error: string) => void;
}

const DEFAULT_MAX_SIZE_MB = 10;
const DEFAULT_ALLOWED_TYPES = [
  'application/pdf',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'application/msword',
  'text/plain',
  'text/markdown',
  'image/png',
  'image/jpeg',
  'image/jpg',
];

export function useChatUpload(options: UseChatUploadOptions) {
  const {
    persona,
    maxSizeMB = DEFAULT_MAX_SIZE_MB,
    allowedTypes = DEFAULT_ALLOWED_TYPES,
    onUploadComplete,
    onIndexed,
    onError,
  } = options;

  const [state, setState] = useState<ChatUploadState>({
    file: null,
    status: 'idle',
    progress: 0,
    error: null,
    docId: null,
    documentMeta: null,
  });

  const fileInputRef = useRef<HTMLInputElement | null>(null);

  // Validate file
  const validateFile = useCallback((file: File): string | null => {
    // Check size
    const maxBytes = maxSizeMB * 1024 * 1024;
    if (file.size > maxBytes) {
      return `El archivo es muy grande. Máximo ${maxSizeMB} MB.`;
    }

    // Check type
    if (allowedTypes.length > 0 && !allowedTypes.includes(file.type)) {
      const ext = file.name.split('.').pop()?.toLowerCase();
      // Also allow by extension for edge cases
      const extAllowed = ['pdf', 'docx', 'doc', 'txt', 'md', 'png', 'jpg', 'jpeg'].includes(ext || '');
      if (!extAllowed) {
        return 'Formato de archivo no soportado. Usa PDF, DOCX, TXT, MD o imagen.';
      }
    }

    return null;
  }, [maxSizeMB, allowedTypes]);

  // Open file picker
  const openFilePicker = useCallback(() => {
    if (!fileInputRef.current) {
      const input = document.createElement('input');
      input.type = 'file';
      input.accept = '.pdf,.docx,.doc,.txt,.md,.png,.jpg,.jpeg';
      input.style.display = 'none';
      document.body.appendChild(input);
      fileInputRef.current = input;
    }

    fileInputRef.current.onchange = (e) => {
      const files = (e.target as HTMLInputElement).files;
      if (files && files.length > 0) {
        handleFileSelect(files[0]);
      }
      // Reset input so same file can be selected again
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    };

    fileInputRef.current.click();
  }, []);

  // Handle file selection (from picker or drag/drop)
  const handleFileSelect = useCallback(async (file: File) => {
    // Validate
    const error = validateFile(file);
    if (error) {
      setState(prev => ({
        ...prev,
        status: 'error',
        error,
        file: null,
      }));
      onError?.(error);
      return;
    }

    // Set file and start upload
    setState(prev => ({
      ...prev,
      file,
      status: 'uploading',
      progress: 0,
      error: null,
      docId: null,
      documentMeta: null,
    }));

    try {
      // Simulate progress (actual upload doesn't have progress events with fetch)
      const progressInterval = setInterval(() => {
        setState(prev => ({
          ...prev,
          progress: Math.min(prev.progress + 10, 90),
        }));
      }, 100);

      // Upload to backend
      const metadata = await uploadDocument(file, {
        assigned_personas: [persona],
        usage_instructions: '', // Will be set after user chooses
      });

      clearInterval(progressInterval);

      setState(prev => ({
        ...prev,
        status: 'pending_instructions',
        progress: 100,
        docId: metadata.doc_id,
        documentMeta: metadata,
      }));

      onUploadComplete?.(metadata);
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Error al subir el archivo';
      setState(prev => ({
        ...prev,
        status: 'error',
        error: errorMsg,
      }));
      onError?.(errorMsg);
    }
  }, [validateFile, persona, onUploadComplete, onError]);

  // Set usage instructions after user selection
  const setInstructions = useCallback(async (instructions: string) => {
    if (!state.docId) {
      log.error('No docId to update');
      return;
    }

    setState(prev => ({
      ...prev,
      status: 'updating',
    }));

    try {
      const updated = await updateDocument(state.docId, {
        usage_instructions: instructions,
      });

      // Document will be processing now
      setState(prev => ({
        ...prev,
        status: 'processing',
        documentMeta: updated,
      }));

      // Poll for indexing completion
      pollForIndexed(state.docId);
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Error al actualizar instrucciones';
      setState(prev => ({
        ...prev,
        status: 'error',
        error: errorMsg,
      }));
      onError?.(errorMsg);
    }
  }, [state.docId, onError]);

  // Poll for document indexing completion
  const pollForIndexed = useCallback(async (docId: string) => {
    const maxAttempts = 30; // 30 seconds max
    let attempts = 0;

    const poll = async () => {
      try {
        const response = await fetch(
          `${process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:7001'}${ROUTES.knowledgeBase}/${docId}`
        );
        const doc = await response.json();

        if (doc.status === 'indexed') {
          setState(prev => ({
            ...prev,
            status: 'indexed',
            documentMeta: doc,
          }));
          onIndexed?.(doc);
          return;
        }

        if (doc.status === 'error') {
          setState(prev => ({
            ...prev,
            status: 'error',
            error: doc.error_message || 'Error al procesar documento',
          }));
          onError?.(doc.error_message || 'Error al procesar documento');
          return;
        }

        // Still processing, continue polling
        attempts++;
        if (attempts < maxAttempts) {
          setTimeout(poll, 1000);
        } else {
          // Timeout but not necessarily error - document might still be processing
          log.warn('Polling timeout, document still processing');
        }
      } catch (err) {
        log.error('Polling error', { error: String(err) });
        // Don't fail on polling errors, just stop
      }
    };

    poll();
  }, [onIndexed, onError]);

  // Cancel/reset
  const cancel = useCallback(() => {
    setState({
      file: null,
      status: 'idle',
      progress: 0,
      error: null,
      docId: null,
      documentMeta: null,
    });
  }, []);

  // Reset after completion
  const reset = useCallback(() => {
    setState({
      file: null,
      status: 'idle',
      progress: 0,
      error: null,
      docId: null,
      documentMeta: null,
    });
  }, []);

  return {
    // State
    file: state.file,
    status: state.status,
    progress: state.progress,
    error: state.error,
    docId: state.docId,
    documentMeta: state.documentMeta,

    // Computed
    isActive: state.status !== 'idle',
    isPending: state.status === 'pending_instructions',
    isProcessing: state.status === 'processing' || state.status === 'updating' || state.status === 'uploading',
    isComplete: state.status === 'indexed',
    isError: state.status === 'error',

    // Actions
    openFilePicker,
    handleFileSelect,
    setInstructions,
    cancel,
    reset,
  };
}

export default useChatUpload;
