/**
 * useDocumentFilters - Search, filter, and computed stats
 *
 * Single responsibility: derives filtered views and aggregate
 * stats from the document collection without mutating it.
 */
'use client';

import { useState, useMemo } from 'react';
import type { DocumentMetadata, DocumentStatus } from '@aurity-standalone/types/knowledge';

export type ViewMode = 'grid' | 'list';

export interface DocumentStats {
  total: number;
  indexed: number;
  processing: number;
  errors: number;
}

interface UseDocumentFiltersReturn {
  searchQuery: string;
  setSearchQuery: (query: string) => void;
  statusFilter: DocumentStatus | 'all';
  setStatusFilter: (status: DocumentStatus | 'all') => void;
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

export function useDocumentFilters(documents: DocumentMetadata[]): UseDocumentFiltersReturn {
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<DocumentStatus | 'all'>('all');
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
    searchQuery,
    setSearchQuery,
    statusFilter,
    setStatusFilter,
    viewMode,
    setViewMode,
    filteredDocuments,
    stats,
  };
}
