/**
 * DocumentList - Document grid/list with loading and empty states
 *
 * Single responsibility: renders documents in the chosen view mode,
 * delegating individual card rendering to DocumentCard.
 */

import { FileText, RefreshCw } from 'lucide-react';
import { DocumentCard } from '@/components/admin/DocumentCard';
import type { ViewMode } from '../hooks/useDocumentFilters';
import type { DocumentMetadata } from '@aurity-standalone/types/knowledge';

interface DocumentListProps {
  documents: DocumentMetadata[];
  viewMode: ViewMode;
  loading: boolean;
  hasDocuments: boolean;
  searchQuery: string;
  deletingId: string | null;
  reindexingId: string | null;
  onPreview: (doc: DocumentMetadata) => void;
  onEdit: (doc: DocumentMetadata) => void;
  onDelete: (docId: string) => void;
  onReindex: (docId: string) => void;
}

export function DocumentList({
  documents,
  viewMode,
  loading,
  hasDocuments,
  searchQuery,
  deletingId,
  reindexingId,
  onPreview,
  onEdit,
  onDelete,
  onReindex,
}: DocumentListProps) {
  // Initial loading state
  if (loading && !hasDocuments) {
    return (
      <div className="kno-page-state">
        <RefreshCw className="kno-page-spinner" />
        <p>Loading documents...</p>
      </div>
    );
  }

  // Empty state
  if (documents.length === 0) {
    return (
      <div className="kno-page-state">
        <FileText className="kno-page-empty-icon" />
        <p className="kno-page-empty-title">No documents found</p>
        <p className="kno-page-empty-hint">
          {searchQuery
            ? 'Try a different search term'
            : 'Upload your first document to get started'}
        </p>
      </div>
    );
  }

  // Document grid/list
  return (
    <div className={viewMode === 'grid' ? 'kno-docs-grid' : 'kno-docs-list'}>
      {documents.map((doc) => (
        <DocumentCard
          key={doc.doc_id}
          document={doc}
          viewMode={viewMode}
          onPreview={() => onPreview(doc)}
          onEdit={() => onEdit(doc)}
          onDelete={() => onDelete(doc.doc_id)}
          onReindex={() => onReindex(doc.doc_id)}
          isDeleting={deletingId === doc.doc_id}
          isReindexing={reindexingId === doc.doc_id}
        />
      ))}
    </div>
  );
}
