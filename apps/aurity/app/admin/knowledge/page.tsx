/**
 * Knowledge Base Admin Page
 *
 * Admin interface for managing documents in the RAG knowledge base.
 * Card: FI-UI-FEAT-021
 */
'use client';

import { useState, useEffect, useCallback } from 'react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from '@/components/ui/select';
import {
  FileText,
  Plus,
  Search,
  RefreshCw,
  AlertCircle,
  LayoutGrid,
  List,
  X,
} from 'lucide-react';
import { AppTemplate } from '@/components/layout/AppTemplate';
import { adminKnowledgeHeader } from '@/config/page-headers';
import { DocumentCard } from '@/components/admin/DocumentCard';
import { DocumentUploadModal } from '@/components/admin/DocumentUploadModal';
import { DocumentEditModal } from '@/components/admin/DocumentEditModal';
import { DocumentPreviewModal } from '@/components/admin/DocumentPreviewModal';
import {
  fetchDocuments,
  deleteDocument,
  reindexDocument,
} from '@aurity-standalone/api-client/knowledge';
import { confirmDelete } from '@/lib/swal';
import type { DocumentMetadata, DocumentStatus } from '@aurity-standalone/types/knowledge';

type ViewMode = 'grid' | 'list';

export default function KnowledgeBasePage() {
  // State
  const [documents, setDocuments] = useState<DocumentMetadata[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>('grid');

  // Filters
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<DocumentStatus | 'all'>('all');

  // Modals
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [editingDocument, setEditingDocument] = useState<DocumentMetadata | null>(null);
  const [previewingDocument, setPreviewingDocument] = useState<DocumentMetadata | null>(null);

  // Actions
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [reindexingId, setReindexingId] = useState<string | null>(null);

  // Load documents
  const loadDocuments = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = statusFilter !== 'all' ? { status: statusFilter } : undefined;
      const response = await fetchDocuments(params);
      setDocuments(response.documents);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load documents');
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => {
    loadDocuments();
  }, [loadDocuments]);

  // Filter documents by search query
  const filteredDocuments = documents.filter((doc) => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      (doc.filename && doc.filename.toLowerCase().includes(query)) ||
      (doc.title && doc.title.toLowerCase().includes(query)) ||
      doc.doc_type.toLowerCase().includes(query)
    );
  });

  // Handle upload success
  const handleUploadSuccess = (newDoc: DocumentMetadata) => {
    setDocuments((prev) => [newDoc, ...prev]);
    setShowUploadModal(false);
  };

  // Handle document update
  const handleDocumentUpdate = (updatedDoc: DocumentMetadata) => {
    setDocuments((prev) =>
      prev.map((doc) => (doc.doc_id === updatedDoc.doc_id ? updatedDoc : doc))
    );
    setEditingDocument(null);
  };

  // Handle delete
  const handleDelete = async (docId: string) => {
    const confirmed = await confirmDelete('este documento');
    if (!confirmed) return;

    setDeletingId(docId);
    try {
      await deleteDocument(docId);
      setDocuments((prev) => prev.filter((doc) => doc.doc_id !== docId));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete document');
    } finally {
      setDeletingId(null);
    }
  };

  // Handle reindex
  const handleReindex = async (docId: string) => {
    setReindexingId(docId);
    try {
      const updated = await reindexDocument(docId);
      setDocuments((prev) =>
        prev.map((doc) => (doc.doc_id === updated.doc_id ? updated : doc))
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to reindex document');
    } finally {
      setReindexingId(null);
    }
  };

  // Stats
  const stats = {
    total: documents.length,
    indexed: documents.filter((d) => d.status === 'indexed').length,
    processing: documents.filter((d) => d.status === 'processing').length,
    errors: documents.filter((d) => d.status === 'error').length,
  };

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

        {/* Stats Grid - Responsive 2x2 on mobile, 4x1 on desktop */}
        <div className="kno-stats-grid">
          <StatCard
            label="Total Documents"
            value={stats.total}
            icon={<FileText className="kno-stat-icon" />}
            color="blue"
          />
          <StatCard
            label="Indexed"
            value={stats.indexed}
            icon={<Search className="kno-stat-icon" />}
            color="emerald"
          />
          <StatCard
            label="Processing"
            value={stats.processing}
            icon={<RefreshCw className={stats.processing > 0 ? 'kno-stat-icon-spin' : 'kno-stat-icon'} />}
            color="yellow"
          />
          <StatCard
            label="Errors"
            value={stats.errors}
            icon={<AlertCircle className="kno-stat-icon" />}
            color="red"
          />
        </div>

        {/* Actions Bar - Stack on mobile, row on desktop */}
        <div className="kno-actions-bar">
          {/* Search & Filter Row */}
          <div className="kno-search-filter-row">
            {/* Search Input */}
            <div className="kno-search-wrap">
              <Input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search documents..."
                variant="default"
                icon={Search}
                className="kno-input-dark"
              />
            </div>

            {/* Status Filter Dropdown */}
            <div className="kno-filter-wrap">
              <Select
                value={statusFilter}
                onValueChange={(value) => setStatusFilter(value as DocumentStatus | 'all')}
              >
                <SelectTrigger className="kno-input-dark">
                  <SelectValue placeholder="All Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Status</SelectItem>
                  <SelectItem value="indexed">Indexed</SelectItem>
                  <SelectItem value="processing">Processing</SelectItem>
                  <SelectItem value="pending">Pending</SelectItem>
                  <SelectItem value="error">Error</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* View Toggle & Actions Row */}
          <div className="kno-actions-right">
            {/* View Mode Toggle */}
            <div className="kno-view-toggle">
              <button
                onClick={() => setViewMode('grid')}
                aria-label="Grid view"
                aria-pressed={viewMode === 'grid'}
                className={viewMode === 'grid' ? 'kno-view-btn-active' : 'kno-view-btn-inactive'}
              >
                <LayoutGrid className="kno-view-icon" />
              </button>
              <button
                onClick={() => setViewMode('list')}
                aria-label="List view"
                aria-pressed={viewMode === 'list'}
                className={viewMode === 'list' ? 'kno-view-btn-active' : 'kno-view-btn-inactive'}
              >
                <List className="kno-view-icon" />
              </button>
            </div>

            {/* Refresh Button */}
            <Button
              variant="ghost"
              size="sm"
              onClick={loadDocuments}
              disabled={loading}
              aria-label="Refresh documents"
              className="kno-refresh-btn"
            >
              <RefreshCw className={loading ? 'kno-refresh-icon-spin' : 'kno-refresh-icon'} />
            </Button>

            {/* Upload Button */}
            <Button
              variant="success"
              size="md"
              icon={Plus}
              onClick={() => setShowUploadModal(true)}
              className="kno-upload-btn"
            >
              <span className="kno-upload-label-desktop">Upload Document</span>
              <span className="kno-upload-label-mobile">Upload</span>
            </Button>
          </div>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="kno-error-alert">
            <AlertCircle className="kno-error-alert-icon" />
            <p className="kno-error-alert-text">{error}</p>
            <button
              onClick={() => setError(null)}
              className="kno-error-dismiss"
              aria-label="Dismiss error"
            >
              <X className="kno-dismiss-icon" />
            </button>
          </div>
        )}

        {/* Documents Grid/List */}
        {loading && documents.length === 0 ? (
          <div className="kno-page-state">
            <RefreshCw className="kno-page-spinner" />
            <p>Loading documents...</p>
          </div>
        ) : filteredDocuments.length === 0 ? (
          <div className="kno-page-state">
            <FileText className="kno-page-empty-icon" />
            <p className="kno-page-empty-title">No documents found</p>
            <p className="kno-page-empty-hint">
              {searchQuery
                ? 'Try a different search term'
                : 'Upload your first document to get started'}
            </p>
          </div>
        ) : (
          <div
            className={
              viewMode === 'grid'
                ? 'kno-docs-grid'
                : 'kno-docs-list'
            }
          >
            {filteredDocuments.map((doc) => (
              <DocumentCard
                key={doc.doc_id}
                document={doc}
                viewMode={viewMode}
                onPreview={() => setPreviewingDocument(doc)}
                onEdit={() => setEditingDocument(doc)}
                onDelete={() => handleDelete(doc.doc_id)}
                onReindex={() => handleReindex(doc.doc_id)}
                isDeleting={deletingId === doc.doc_id}
                isReindexing={reindexingId === doc.doc_id}
              />
            ))}
          </div>
        )}
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

// =============================================================================
// STAT CARD COMPONENT
// =============================================================================

interface StatCardProps {
  label: string;
  value: number;
  icon: React.ReactNode;
  color: 'blue' | 'emerald' | 'yellow' | 'red';
}

const STAT_COLORS = {
  blue: 'kno-stat-color-blue',
  emerald: 'kno-stat-color-emerald',
  yellow: 'kno-stat-color-yellow',
  red: 'kno-stat-color-red',
} as const;

function StatCard({ label, value, icon, color }: StatCardProps) {
  return (
    <div className={`kno-stat-card ${STAT_COLORS[color]}`}>
      <div className="kno-stat-inner">
        <div className="kno-stat-icon-box">
          {icon}
        </div>
        <div className="kno-stat-text-wrap">
          <p className="kno-stat-value">
            {value}
          </p>
          <p className="kno-stat-label">
            {label}
          </p>
        </div>
      </div>
    </div>
  );
}
