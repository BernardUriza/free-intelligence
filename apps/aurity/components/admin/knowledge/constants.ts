/**
 * Knowledge Base Constants
 *
 * Shared constants for document cards, modals, and persona configuration.
 * Card: FI-UI-FEAT-021
 */

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
  Bot,
  Stethoscope,
  Hand,
  Sparkles,
  MessageCircle,
} from 'lucide-react';
import type { QuestionSource } from '@aurity-standalone/types/knowledge';
import type { DocumentType, DocumentStatus } from '@aurity-standalone/types/knowledge';

// =============================================================================
// DOCUMENT TYPE ICONS
// =============================================================================

export const TYPE_ICONS: Record<DocumentType, typeof FileText> = {
  pdf: FileText,
  docx: FileText,
  markdown: FileCode,
  text: File,
  image: ImageIcon,
  unknown: FileQuestion,
};

// =============================================================================
// DOCUMENT STATUS CONFIG
// =============================================================================

export const STATUS_CONFIG: Record<DocumentStatus, {
  icon: typeof Clock;
  color: string;
  label: string;
  labelEn: string;
}> = {
  pending: {
    icon: Clock,
    color: 'text-yellow-400',
    label: 'Pendiente',
    labelEn: 'Pending',
  },
  processing: {
    icon: Loader2,
    color: 'fi-text-primary',
    label: 'Procesando',
    labelEn: 'Processing',
  },
  indexed: {
    icon: CheckCircle,
    color: 'fi-text-success',
    label: 'Indexado',
    labelEn: 'Indexed',
  },
  error: {
    icon: AlertCircle,
    color: 'fi-text-error',
    label: 'Error',
    labelEn: 'Error',
  },
};

// =============================================================================
// PERSONA ICONS & COLORS
// =============================================================================

export const PERSONA_ICONS: Record<string, typeof Bot> = {
  general_assistant: Bot,
  clinical_advisor: Stethoscope,
  soap_editor: FileText,
  onboarding_guide: Hand,
};

export const PERSONA_COLORS: Record<string, string> = {
  general_assistant: 'bg-purple-900/50 text-purple-300 border-purple-700/50',
  clinical_advisor: 'bg-emerald-900/50 text-emerald-300 border-emerald-700/50',
  soap_editor: 'bg-blue-900/50 text-blue-300 border-blue-700/50',
  onboarding_guide: 'bg-amber-900/50 text-amber-300 border-amber-700/50',
};

// =============================================================================
// QUESTION SOURCE CONFIG
// =============================================================================

export const QUESTION_SOURCE_CONFIG: Record<QuestionSource, {
  label: string;
  icon: typeof Sparkles;
  bgClass: string;
  textClass: string;
}> = {
  llm_initial: {
    label: 'Generadas por IA',
    icon: Sparkles,
    bgClass: 'kno-qgroup-ai-bg',
    textClass: 'kno-qgroup-ai-text',
  },
  user_query: {
    label: 'Preguntas de Usuarios',
    icon: MessageCircle,
    bgClass: 'kno-qgroup-user-bg',
    textClass: 'kno-qgroup-user-text',
  },
};

// =============================================================================
// HELPERS
// =============================================================================

/**
 * Format persona ID to readable label
 * @example "general_assistant" -> "General Assistant"
 */
export function formatPersonaLabel(personaId: string): string {
  return personaId
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (l) => l.toUpperCase())
    .split(' ')
    .slice(0, 2)
    .join(' ');
}

/**
 * Format ISO timestamp to relative time in Spanish
 * @example "2025-01-03T10:00:00Z" -> "hace 2 min"
 */
export function formatRelativeTime(isoTimestamp: string): string {
  const date = new Date(isoTimestamp);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHour = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHour / 24);

  if (diffSec < 60) return 'ahora';
  if (diffMin < 60) return `hace ${diffMin} min`;
  if (diffHour < 24) return `hace ${diffHour}h`;
  if (diffDay < 7) return `hace ${diffDay}d`;
  return date.toLocaleDateString('es-MX', { day: 'numeric', month: 'short' });
}

// =============================================================================
// FILE VALIDATION
// =============================================================================

export const ACCEPTED_EXTENSIONS = '.pdf,.docx,.md,.txt,.png,.jpg,.jpeg';
export const MAX_FILE_SIZE_MB = 50;
export const MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024;

export const VALID_EXTENSIONS = ['pdf', 'docx', 'md', 'txt', 'png', 'jpg', 'jpeg'];

export function validateFile(file: File): { valid: boolean; error?: string } {
  // Check file size
  if (file.size > MAX_FILE_SIZE_BYTES) {
    return {
      valid: false,
      error: `El archivo es demasiado grande. Máximo ${MAX_FILE_SIZE_MB}MB.`,
    };
  }

  // Check file type
  const ext = file.name.split('.').pop()?.toLowerCase();
  if (!ext || !VALID_EXTENSIONS.includes(ext)) {
    return {
      valid: false,
      error: `Tipo de archivo no soportado. Usa: ${VALID_EXTENSIONS.join(', ')}`,
    };
  }

  return { valid: true };
}
