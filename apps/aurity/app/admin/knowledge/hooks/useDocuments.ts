/**
 * useDocuments - Document CRUD operations and state management
 *
 * Single responsibility: manages document collection state,
 * loading, and all mutation operations (delete, reindex).
 */
'use client';

import { useState, useEffect, useCallback } from 'react';
import {
  fetchDocuments,
  deleteDocument,
  reindexDocument,
} from '@aurity-standalone/api-client/knowledge';
import { confirmDelete } from '@/lib/swal';
import type { DocumentMetadata, DocumentStatus } from '@aurity-standalone/types/knowledge';

interface UseDocumentsOptions {
  statusFilter?: DocumentStatus | 'all';
}

interface UseDocumentsReturn {
  documents: DocumentMetadata[];
  loading: boolean;
  error: string | null;
  deletingId: string | null;
  reindexingId: string | null;
  loadDocuments: () => Promise<void>;
  clearError: () => void;
  addDocument: (doc: DocumentMetadata) => void;
  updateDocument: (doc: DocumentMetadata) => void;
  handleDelete: (docId: string) => Promise<void>;
  handleReindex: (docId: string) => Promise<void>;
}

function extractErrorMessage(err: unknown): string {
  return err instanceof Error ? err.message : String(err);
}

export function useDocuments({ statusFilter = 'all' }: UseDocumentsOptions = {}): UseDocumentsReturn {
  const [documents, setDocuments] = useState<DocumentMetadata[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [reindexingId, setReindexingId] = useState<string | null>(null);

  const loadDocuments = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = statusFilter !== 'all' ? { status: statusFilter } : undefined;
      const response = await fetchDocuments(params);
      setDocuments(response.documents);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => {
    loadDocuments();
  }, [loadDocuments]);

  const clearError = useCallback(() => setError(null), []);

  const addDocument = useCallback((doc: DocumentMetadata) => {
    setDocuments((prev) => [doc, ...prev]);
  }, []);

  const updateDocument = useCallback((updatedDoc: DocumentMetadata) => {
    setDocuments((prev) =>
      prev.map((doc) => (doc.doc_id === updatedDoc.doc_id ? updatedDoc : doc)),
    );
  }, []);

  const handleDelete = useCallback(async (docId: string) => {
    const confirmed = await confirmDelete('este documento');
    if (!confirmed) return;

    setDeletingId(docId);
    try {
      await deleteDocument(docId);
      setDocuments((prev) => prev.filter((doc) => doc.doc_id !== docId));
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setDeletingId(null);
    }
  }, []);

  const handleReindex = useCallback(async (docId: string) => {
    setReindexingId(docId);
    try {
      const updated = await reindexDocument(docId);
      setDocuments((prev) =>
        prev.map((doc) => (doc.doc_id === updated.doc_id ? updated : doc)),
      );
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setReindexingId(null);
    }
  }, []);

  return {
    documents,
    loading,
    error,
    deletingId,
    reindexingId,
    loadDocuments,
    clearError,
    addDocument,
    updateDocument,
    handleDelete,
    handleReindex,
  };
}
