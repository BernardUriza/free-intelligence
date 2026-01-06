/**
 * DocumentCardActions Component
 *
 * Action buttons for document cards (Preview, Edit, Reindex, Delete).
 * Extracted for better reusability and testability.
 * Card: FI-UI-FEAT-021
 */

'use client';

import { Edit, Trash2, RefreshCw, Eye, Loader2 } from 'lucide-react';

// =============================================================================
// TYPES
// =============================================================================

export interface DocumentCardActionsProps {
  onPreview: () => void;
  onEdit: () => void;
  onDelete: () => void;
  onReindex: () => void;
  isDeleting?: boolean;
  isReindexing?: boolean;
  isProcessing?: boolean;
  /** Show actions always (mobile) or on hover (desktop) */
  alwaysVisible?: boolean;
}

interface ActionButtonProps {
  onClick: () => void;
  disabled?: boolean;
  'aria-label': string;
  className?: string;
  variant?: 'default' | 'danger' | 'success';
  children: React.ReactNode;
}

// =============================================================================
// ACTION BUTTON SUB-COMPONENT
// =============================================================================

function ActionButton({
  onClick,
  disabled,
  'aria-label': ariaLabel,
  className = '',
  variant = 'default',
  children,
}: ActionButtonProps) {
  const baseClasses = 'p-1.5 sm:p-2 rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed';

  const variantClasses = {
    default: 'text-slate-400 hover:text-slate-200 hover:bg-slate-700/50',
    danger: 'text-slate-400 hover:text-red-400 hover:bg-red-900/30',
    success: 'text-slate-400 hover:text-emerald-300 hover:bg-emerald-900/30',
  };

  return (
    <button
      onClick={onClick}
      disabled={disabled}
      aria-label={ariaLabel}
      className={`${baseClasses} ${variantClasses[variant]} ${className}`}
    >
      {children}
    </button>
  );
}

// =============================================================================
// MAIN COMPONENT
// =============================================================================

export function DocumentCardActions({
  onPreview,
  onEdit,
  onDelete,
  onReindex,
  isDeleting = false,
  isReindexing = false,
  isProcessing = false,
  alwaysVisible = false,
}: DocumentCardActionsProps) {
  const isActionDisabled = isDeleting || isReindexing;

  const visibilityClasses = alwaysVisible
    ? 'opacity-100'
    : 'sm:opacity-0 sm:group-hover:opacity-100 transition-opacity';

  return (
    <div className={`flex items-center gap-0.5 sm:gap-1 flex-shrink-0 ${visibilityClasses}`}>
      {/* Preview */}
      <ActionButton
        onClick={onPreview}
        disabled={isActionDisabled}
        aria-label="Preview document"
        variant="success"
      >
        <Eye className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
      </ActionButton>

      {/* Edit */}
      <ActionButton
        onClick={onEdit}
        disabled={isActionDisabled}
        aria-label="Edit document"
      >
        <Edit className="w-3.5 h-3.5 sm:w-4 sm:h-4" />
      </ActionButton>

      {/* Reindex */}
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

      {/* Delete */}
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
  );
}

export default DocumentCardActions;
