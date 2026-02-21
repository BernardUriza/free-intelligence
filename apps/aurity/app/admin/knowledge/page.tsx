/**
 * Knowledge Base Admin Page
 *
 * Admin interface for managing documents in the RAG knowledge base.
 * Card: FI-UI-FEAT-021
 */
'use client';

import { useState, useCallback } from 'react';
import { AlertCircle, X } from 'lucide-react';
import { AppTemplate } from '@/components/layout/AppTemplate';
import { adminKnowledgeHeader } from '@/config/page-headers';
import { DocumentUploadModal } from '@/components/admin/DocumentUploadModal';
import { DocumentEditModal } from '@/components/admin/DocumentEditModal';
import { DocumentPreviewModal } from '@/components/admin/DocumentPreviewModal';
import { useDocuments } from './hooks/useDocuments';
import { useDocumentFilters } from './hooks/useDocumentFilters';
import { KnowledgeStatsGrid } from './components/KnowledgeStatsGrid';
import { KnowledgeActionsBar } from './components/KnowledgeActionsBar';
import { DocumentList } from './components/DocumentList';
import type { DocumentMetadata } from '@aurity-standalone/types/knowledge';

export default function KnowledgeBasePage() {
  // Data layer
  const {
    searchQuery,
    setSearchQuery,
    statusFilter,
    setStatusFilter,
    viewMode,
    setViewMode,
    filteredDocuments,
    stats,
  } = useDocumentFiltersWithDocuments();

  return null; // placeholder — replaced below
}

// ── Composed page (actual implementation) ────────────────────────────

// We need filters.statusFilter before constructing useDocuments,
// so we compose them inside the page component directly.

KnowledgeBasePage.displayName = 'KnowledgeBasePage';

// Override the default export with the real implementation:
// eslint-disable-next-line import/no-anonymous-default-export
export default function KnowledgeBasePage() {
  // Filters (owns search, status, viewMode state)
  // We initialize filters first to get statusFilter for the data hook.
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<
    import('@aurity-standalone/types/knowledge').DocumentStatus | 'all'
  >('all');

  // Documents CRUD
  const {
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
  } = useDocuments({ statusFilter });

  // Derived filters & stats
  const { viewMode, setViewMode, filteredDocuments, stats } = useDocumentFilters(documents);

  // Modals
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [editingDocument, setEditingDocument] = useState<DocumentMetadata | null>(null);
  const [previewingDocument, setPreviewingDocument] = useState<DocumentMetadata | null>(null);

  const handleUploadSuccess = useCallback(
    (newDoc: DocumentMetadata) => {
      addDocument(newDoc);
      setShowUploadModal(false);
    },
    [addDocument],
  );

  const handleDocumentUpdate = useCallback(
    (updatedDoc: DocumentMetadata) => {
      updateDocument(updatedDoc);
      setEditingDocument(null);
    },
    [updateDocument],
  );

  const headerConfig = adminKnowledgeHeader({
    documentsCount: stats.total,
    indexedCount: stats.indexed,
  });

  return (
    <AppTemplate
      headerConfig={headerConfig}
      backgroundGradient="emerald"
      padding="8"
      showWatermark={true}
      showGeometricBg={true}
    >
      <div className="kno-page-container">
        <KnowledgeStatsGrid stats={stats} />

        <KnowledgeActionsBar
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
          statusFilter={statusFilter}
          onStatusFilterChange={setStatusFilter}
          viewMode={viewMode}
          onViewModeChange={setViewMode}
          loading={loading}
          onRefresh={loadDocuments}
          onUpload={() => setShowUploadModal(true)}
        />

        {/* Error Alert */}
        {error && (
          <div className="kno-error-alert">
            <AlertCircle className="kno-error-alert-icon" />
            <p className="kno-error-alert-text">{error}</p>
            <button
              onClick={clearError}
              className="kno-error-dismiss"
              aria-label="Dismiss error"
            >
              <X className="kno-dismiss-icon" />
            </button>
          </div>
        )}

        <DocumentList
          documents={filteredDocuments}
          viewMode={viewMode}
          loading={loading}
          hasDocuments={documents.length > 0}
          searchQuery={searchQuery}
          deletingId={deletingId}
          reindexingId={reindexingId}
          onPreview={(doc) => setPreviewingDocument(doc)}
          onEdit={(doc) => setEditingDocument(doc)}
          onDelete={handleDelete}
          onReindex={handleReindex}
        />
      </div>

      {/* Modals */}
      <DocumentUploadModal
        isOpen={showUploadModal}
        onClose={() => setShowUploadModal(false)}
        onSuccess={handleUploadSuccess}
      />

      <DocumentEditModal
        isOpen={editingDocument !== null}
        onClose={() => setEditingDocument(null)}
        document={editingDocument}
        onUpdate={handleDocumentUpdate}
      />

      <DocumentPreviewModal
        isOpen={previewingDocument !== null}
        onClose={() => setPreviewingDocument(null)}
        document={previewingDocument}
      />
    </AppTemplate>
  );
}
