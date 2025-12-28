/**
 * DocumentCard Component
 *
 * Displays a document in grid/list view with metadata, status, and actions.
 * Fully responsive with proper touch targets and text truncation.
 * Card: FI-UI-FEAT-021
 */

'use client';

import {
  FileText,
  FileCode,
  Image as ImageIcon,
  File,
  FileQuestion,
  Clock,
  Loader2,
  CheckCircle,
  AlertCircle,
  Edit,
  Trash2,
  RefreshCw,
  Bot,
  Stethoscope,
  Hand,
  Eye,
} from 'lucide-react';
import type { DocumentMetadata, DocumentType, DocumentStatus } from '@aurity-standalone/types/knowledge';
import { formatFileSize, formatDate } from '@aurity-standalone/api-client/knowledge';

// =============================================================================
// TYPES & CONSTANTS
// =============================================================================

interface DocumentCardProps {
  document: DocumentMetadata;
  viewMode?: 'grid' | 'list';
  onPreview: () => void;
  onEdit: () => void;
  onDelete: () => void;
  onReindex: () => void;
  isDeleting?: boolean;
  isReindexing?: boolean;
}

const TYPE_ICONS: Record<DocumentType, typeof FileText> = {
  pdf: FileText,
  docx: FileText,
  markdown: FileCode,
  text: File,
  image: ImageIcon,
  unknown: FileQuestion,
};

const STATUS_CONFIG: Record<DocumentStatus, { icon: typeof Clock; color: string; label: string }> = {
  pending: { icon: Clock, color: 'text-yellow-400', label: 'Pendiente' },
  processing: { icon: Loader2, color: 'fi-text-primary', label: 'Procesando' },
  indexed: { icon: CheckCircle, color: 'fi-text-success', label: 'Indexado' },
  error: { icon: AlertCircle, color: 'fi-text-error', label: 'Error' },
};

const PERSONA_ICONS: Record<string, typeof Bot> = {
  general_assistant: Bot,
  clinical_advisor: Stethoscope,
  soap_editor: FileText,
  onboarding_guide: Hand,
};

const PERSONA_COLORS: Record<string, string> = {
  general_assistant: 'bg-purple-900/50 text-purple-300 border-purple-700/50',
  clinical_advisor: 'bg-emerald-900/50 text-emerald-300 border-emerald-700/50',
  soap_editor: 'bg-blue-900/50 text-blue-300 border-blue-700/50',
  onboarding_guide: 'bg-amber-900/50 text-amber-300 border-amber-700/50',
};

// Format persona ID to readable label
function formatPersonaLabel(personaId: string): string {
  return personaId
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (l) => l.toUpperCase())
    .split(' ')
    .slice(0, 2)
    .join(' ');
}

// =============================================================================
// MAIN COMPONENT
// =============================================================================

export function DocumentCard({
  document,
  viewMode = 'grid',
  onPreview,
  onEdit,
  onDelete,
  onReindex,
  isDeleting,
  isReindexing,
}: DocumentCardProps) {
  const TypeIcon = TYPE_ICONS[document.doc_type] || FileQuestion;
  const statusConfig = STATUS_CONFIG[document.status];
  const StatusIcon = statusConfig.icon;
  const isProcessing = document.status === 'processing';
  const isActionDisabled = isDeleting || isReindexing;

  const displayTitle = document.title || document.filename || 'Untitled';

  return (
    <article
      className={viewMode === 'list' ? 'fi-doc-card-list' : 'fi-doc-card'}
    >
      {/* Header Section */}
      <div className={`flex items-start gap-3 ${viewMode === 'list' ? 'flex-1 min-w-0' : 'mb-3'}`}>
        {/* Document Type Icon */}
        <div className="flex-shrink-0 p-2 rounded-lg bg-slate-700/50 border border-slate-600/50">
          <TypeIcon className="w-4 h-4 sm:w-5 sm:h-5 fi-text" />
        </div>

        {/* Title & Filename */}
        <div className="flex-1 min-w-0">
          <h3
            className="text-sm sm:text-base font-semibold text-white truncate"
            title={displayTitle}
          >
            {displayTitle}
          </h3>
          {document.title && document.filename && (
            <p className="text-[10px] sm:fi-text-xs-muted truncate mt-0.5">
              {document.filename}
            </p>
          )}
        </div>

        {/* Actions - Always visible on mobile, hover on desktop */}
        <div className="flex items-center gap-0.5 sm:gap-1 flex-shrink-0 sm:opacity-0 sm:group-hover:opacity-100 transition-opacity">
          <ActionButton
            onClick={onPreview}
            disabled={isActionDisabled}
            aria-label="Preview document"
            className="fi-text-success hover:text-emerald-300 hover:bg-emerald-900/30"
          >
            <Eye className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
          </ActionButton>
          <ActionButton
            onClick={onEdit}
            disabled={isActionDisabled}
            aria-label="Edit document"
          >
            <Edit className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
          </ActionButton>
          <ActionButton
            onClick={onReindex}
            disabled={isProcessing || isActionDisabled}
            aria-label="Reindex document"
            className={isReindexing ? 'fi-text-primary' : ''}
          >
            <RefreshCw
              className={`w-3.5 h-3.5 sm:w-4 sm:h-4 ${isReindexing ? 'animate-spin' : ''}`}
            />
          </ActionButton>
          <ActionButton
            onClick={onDelete}
            disabled={isActionDisabled}
            aria-label="Delete document"
            variant="danger"
          >
            {isDeleting ? (
              <Loader2 className="w-3.5 h-3.5 sm:w-4 sm:h-4 animate-spin" />
            ) : (
              <Trash2 className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
            )}
          </ActionButton>
        </div>
      </div>

      {/* Content Section */}
      <div className={viewMode === 'list' ? 'flex-1 min-w-0 space-y-2' : 'space-y-3'}>
        {/* Metadata Row */}
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-[10px] sm:fi-text-xs">
          <span className="uppercase font-medium tracking-wide">
            {document.doc_type}
          </span>
          <span className="text-slate-600 hidden sm:inline">|</span>
          <span>{formatFileSize(document.size_bytes)}</span>
          <span className="text-slate-600 hidden sm:inline">|</span>
          <span className="hidden sm:inline">{formatDate(document.uploaded_at)}</span>
        </div>

        {/* Assigned Personas */}
        {document.assigned_personas && document.assigned_personas.length > 0 && (
          <div className="flex flex-wrap gap-1 sm:gap-1.5">
            {document.assigned_personas.map((personaId) => {
              const PersonaIcon = PERSONA_ICONS[personaId] || Bot;
              const colorClass = PERSONA_COLORS[personaId] || 'bg-slate-700 fi-text border-slate-600/50';
              return (
                <span
                  key={personaId}
                  className={`fi-persona-chip ${colorClass}`}
                >
                  <PersonaIcon className="w-2.5 h-2.5 sm:w-3 sm:h-3" />
                  <span className="truncate max-w-[80px] sm:max-w-none">
                    {formatPersonaLabel(personaId)}
                  </span>
                </span>
              );
            })}
          </div>
        )}

        {/* Usage Instructions Preview */}
        {document.usage_instructions && (
          <p
            className="text-[10px] sm:fi-text-xs italic line-clamp-2"
            title={document.usage_instructions}
          >
            &ldquo;{document.usage_instructions}&rdquo;
          </p>
        )}
      </div>

      {/* Status Footer */}
      <div
        className={`
          flex items-center justify-between gap-2
          pt-3 mt-3
          fi-border-top/50
          ${viewMode === 'list' ? 'sm:border-t-0 sm:pt-0 sm:mt-0 sm:border-l sm:pl-4' : ''}
        `}
      >
        <div className={`flex items-center gap-1.5 ${statusConfig.color}`}>
          <StatusIcon
            className={`w-3.5 h-3.5 sm:w-4 sm:h-4 ${isProcessing ? 'animate-spin' : ''}`}
          />
          <span className="text-[10px] sm:fi-text-xs-medium">
            {statusConfig.label}
          </span>
          {document.status === 'indexed' && document.chunks_count > 0 && (
            <span className="text-[10px] sm:fi-text-xs-muted">
              ({document.chunks_count} chunks)
            </span>
          )}
        </div>

        {document.status === 'error' && document.error_message && (
          <span
            className="text-[10px] sm:text-xs fi-text-error truncate max-w-[100px] sm:max-w-[150px]"
            title={document.error_message}
          >
            {document.error_message}
          </span>
        )}
      </div>
    </article>
  );
}

// =============================================================================
// ACTION BUTTON SUB-COMPONENT
// =============================================================================

interface ActionButtonProps {
  onClick: () => void;
  disabled?: boolean;
  'aria-label': string;
  className?: string;
  variant?: 'default' | 'danger';
  children: React.ReactNode;
}

function ActionButton({
  onClick,
  disabled,
  'aria-label': ariaLabel,
  className = '',
  variant = 'default',
  children,
}: ActionButtonProps) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      aria-label={ariaLabel}
      className={`${variant === 'danger' ? 'fi-action-btn-danger' : 'fi-action-btn-default'} ${className}`}
    >
      {children}
    </button>
  );
}
