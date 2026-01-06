/**
 * Knowledge Base Components
 *
 * Re-exports for cleaner imports.
 * Usage: import { DocumentCardActions, TYPE_ICONS } from '@/components/admin/knowledge';
 */

export { DocumentCardActions } from './DocumentCardActions';
export type { DocumentCardActionsProps } from './DocumentCardActions';

export {
  TYPE_ICONS,
  STATUS_CONFIG,
  PERSONA_ICONS,
  PERSONA_COLORS,
  QUESTION_SOURCE_CONFIG,
  formatPersonaLabel,
  formatRelativeTime,
  ACCEPTED_EXTENSIONS,
  MAX_FILE_SIZE_MB,
  MAX_FILE_SIZE_BYTES,
  VALID_EXTENSIONS,
  validateFile,
} from './constants';
