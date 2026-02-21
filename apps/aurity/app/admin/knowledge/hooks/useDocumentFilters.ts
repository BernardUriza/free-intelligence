/**
 * useDocumentFilters - View mode, filtered results, and computed stats
 *
 * Single responsibility: derives filtered views and aggregate
 * stats from the document collection without mutating it.
 *
 * searchQuery and statusFilter are owned by the page component
 * so they can be passed to both useDocuments and UI controls.
 */
'use client';

import { useState, useMemo } from 'react';
import type { DocumentMetadata } from '@aurity-standalone/types/knowledge';

export type ViewMode = 'grid' | 'list';

export interface DocumentStats {
  total: number;
  indexed: number;
  processing: number;
  errors: number;
}

interface UseDocumentFiltersOptions {
  documents: DocumentMetadata[];
  searchQuery: string;
}

interface UseDocumentFiltersReturn {
  viewMode: ViewMode;
  setViewMode: (mode: ViewMode) => void;
  filteredDocuments: DocumentMetadata[];
  stats: DocumentStats;
}

function matchesSearch(doc: DocumentMetadata, query: string): boolean {
  const q = query.toLowerCase();
  return (
    (doc.filename?.toLowerCase().includes(q) ?? false) ||
    (doc.title?.toLowerCase().includes(q) ?? false) ||
    doc.doc_type.toLowerCase().includes(q)
  );
}

function computeStats(documents: DocumentMetadata[]): DocumentStats {
  return {
    total: documents.length,
    indexed: documents.filter((d) => d.status === 'indexed').length,
    processing: documents.filter((d) => d.status === 'processing').length,
    errors: documents.filter((d) => d.status === 'error').length,
  };
}

export function useDocumentFilters({
  documents,
  searchQuery,
}: UseDocumentFiltersOptions): UseDocumentFiltersReturn {
  const [viewMode, setViewMode] = useState<ViewMode>('grid');

  const filteredDocuments = useMemo(
    () =>
      searchQuery
        ? documents.filter((doc) => matchesSearch(doc, searchQuery))
        : documents,
    [documents, searchQuery],
  );

  const stats = useMemo(() => computeStats(documents), [documents]);

  return {
    viewMode,
    setViewMode,
    filteredDocuments,
    stats,
  };
}
