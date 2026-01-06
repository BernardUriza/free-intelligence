/**
 * DocumentCard Component
 *
 * Displays a document in grid/list view with metadata, status, and actions.
 * Fully responsive with proper touch targets and text truncation.
 * Card: FI-UI-FEAT-021
 */

'use client';

import { FileQuestion, Bot } from 'lucide-react';
import type { DocumentMetadata } from '@aurity-standalone/types/knowledge';
import { formatFileSize, formatDate } from '@aurity-standalone/api-client/knowledge';
import { DocumentCardActions } from './knowledge/DocumentCardActions';
import {
  TYPE_ICONS,
  STATUS_CONFIG,
  PERSONA_ICONS,
  PERSONA_COLORS,
  formatPersonaLabel,
} from './knowledge/constants';

// =============================================================================
// TYPES
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

  const displayTitle = document.title || document.filename || 'Untitled';

  return (
    <article
      className={`group ${viewMode === 'list' ? 'fi-doc-card-list' : 'fi-doc-card'}`}
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

        {/* Actions */}
        <DocumentCardActions
          onPreview={onPreview}
          onEdit={onEdit}
          onDelete={onDelete}
          onReindex={onReindex}
          isDeleting={isDeleting}
          isReindexing={isReindexing}
          isProcessing={isProcessing}
        />
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

export default DocumentCard;
