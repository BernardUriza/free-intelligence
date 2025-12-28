/**
 * ClinicalNotes - Professional SOAP Notes Editor
 *
 * Modular structure refactored 2025-12:
 * - types.ts: TypeScript interfaces
 * - constants.ts: Static data and configuration
 * - utils.ts: Pure helper functions
 * - components/: Reusable sub-components
 * - hooks/: Custom React hooks
 * - modals/: Modal dialogs
 */

export { ClinicalNotes } from './ClinicalNotes';
export type {
  ClinicalNotesProps,
  SOAPData,
  VitalSigns,
  Medication,
  Diagnosis,
  ChatMessage,
  AISuggestion,
} from './types';
