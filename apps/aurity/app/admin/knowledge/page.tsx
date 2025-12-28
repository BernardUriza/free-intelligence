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
      <div className="max-w-7xl mx-auto space-y-6 lg:space-y-8">

        {/* Stats Grid - Responsive 2x2 on mobile, 4x1 on desktop */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
          <StatCard
            label="Total Documents"
            value={stats.total}
            icon={<FileText className="w-4 h-4 sm:w-5 sm:h-5" />}
            color="blue"
          />
          <StatCard
            label="Indexed"
            value={stats.indexed}
            icon={<Search className="w-4 h-4 sm:w-5 sm:h-5" />}
            color="emerald"
          />
          <StatCard
            label="Processing"
            value={stats.processing}
            icon={<RefreshCw className={`w-4 h-4 sm:w-5 sm:h-5 ${stats.processing > 0 ? 'animate-spin' : ''}`} />}
            color="yellow"
          />
          <StatCard
            label="Errors"
            value={stats.errors}
            icon={<AlertCircle className="w-4 h-4 sm:w-5 sm:h-5" />}
            color="red"
          />
        </div>

        {/* Actions Bar - Stack on mobile, row on desktop */}
        <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          {/* Search & Filter Row */}
          <div className="flex flex-col sm:flex-row gap-3 flex-1 lg:max-w-2xl">
            {/* Search Input */}
            <div className="flex-1 min-w-0">
              <Input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search documents..."
                variant="default"
                icon={Search}
                className="w-full bg-slate-900"
              />
            </div>

            {/* Status Filter Dropdown */}
            <div className="w-full sm:w-40">
              <Select
                value={statusFilter}
                onValueChange={(value) => setStatusFilter(value as DocumentStatus | 'all')}
              >
                <SelectTrigger className="w-full bg-slate-900">
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
          <div className="flex items-center gap-2 sm:gap-3 justify-between sm:justify-end">
            {/* View Mode Toggle */}
            <div className="flex bg-slate-900 border border-slate-700 rounded-lg overflow-hidden">
              <button
                onClick={() => setViewMode('grid')}
                aria-label="Grid view"
                aria-pressed={viewMode === 'grid'}
                className={`p-2 sm:p-2.5 transition-colors ${
                  viewMode === 'grid'
                    ? 'bg-slate-700 text-slate-100'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
                }`}
              >
                <LayoutGrid className="w-4 h-4" />
              </button>
              <button
                onClick={() => setViewMode('list')}
                aria-label="List view"
                aria-pressed={viewMode === 'list'}
                className={`p-2 sm:p-2.5 transition-colors ${
                  viewMode === 'list'
                    ? 'bg-slate-700 text-slate-100'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
                }`}
              >
                <List className="w-4 h-4" />
              </button>
            </div>

            {/* Refresh Button */}
            <Button
              variant="ghost"
              size="sm"
              onClick={loadDocuments}
              disabled={loading}
              aria-label="Refresh documents"
              className="p-2 sm:p-2.5"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </Button>

            {/* Upload Button */}
            <Button
              variant="success"
              size="md"
              icon={Plus}
              onClick={() => setShowUploadModal(true)}
              className="whitespace-nowrap"
            >
              <span className="hidden sm:inline">Upload Document</span>
              <span className="sm:hidden">Upload</span>
            </Button>
          </div>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="flex items-start sm:items-center gap-3 p-3 sm:p-4 bg-red-900/30 border border-red-700 rounded-lg text-red-300">
            <AlertCircle className="w-5 h-5 flex-shrink-0 mt-0.5 sm:mt-0" />
            <p className="flex-1 text-sm sm:text-base">{error}</p>
            <button
              onClick={() => setError(null)}
              className="p-1 fi-text-error hover:text-red-200 transition-colors"
              aria-label="Dismiss error"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Documents Grid/List */}
        {loading && documents.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 sm:py-16 text-slate-400">
            <RefreshCw className="w-8 h-8 animate-spin mb-4" />
            <p>Loading documents...</p>
          </div>
        ) : filteredDocuments.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 sm:py-16 text-slate-400">
            <FileText className="w-10 h-10 sm:w-12 sm:h-12 mb-4 opacity-50" />
            <p className="text-base sm:text-lg font-medium mb-2">No documents found</p>
            <p className="text-sm text-center px-4">
              {searchQuery
                ? 'Try a different search term'
                : 'Upload your first document to get started'}
            </p>
          </div>
        ) : (
          <div
            className={
              viewMode === 'grid'
                ? 'grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-3 sm:gap-4'
                : 'flex flex-col gap-3'
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
  blue: 'bg-blue-900/30 border-blue-700/50 fi-text-primary',
  emerald: 'bg-emerald-900/30 border-emerald-700/50 fi-text-success',
  yellow: 'bg-yellow-900/30 border-yellow-700/50 text-yellow-400',
  red: 'bg-red-900/30 border-red-700/50 fi-text-error',
} as const;

function StatCard({ label, value, icon, color }: StatCardProps) {
  return (
    <div
      className={`
        p-3 sm:p-4
        rounded-lg sm:rounded-xl
        border
        ${STAT_COLORS[color]}
        transition-all duration-200
        hover:brightness-110
      `}
    >
      <div className="flex items-center gap-2 sm:gap-3">
        <div className="p-1.5 sm:p-2 rounded-md sm:rounded-lg bg-slate-900/50 flex-shrink-0">
          {icon}
        </div>
        <div className="min-w-0">
          <p className="text-xl sm:text-2xl font-bold text-slate-100 tabular-nums">
            {value}
          </p>
          <p className="text-[10px] sm:text-xs opacity-80 truncate">
            {label}
          </p>
        </div>
      </div>
    </div>
  );
}
