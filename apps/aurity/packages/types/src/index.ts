/**
 * @aurity-standalone/types
 *
 * Comprehensive TypeScript type definitions for Aurity healthcare platform.
 * Includes types for medical workflows, AI assistants, patient check-in,
 * LLM configuration, and more.
 *
 * @packageDocumentation
 */

// Assistant & Chat
export * from './assistant';
export * from './chat';

// Medical - exclude Patient (use from patient.ts which has more fields)
export type { ClinicalNote, Order, Encounter, WorkflowState, MedicalWorkflowProps, WorkflowStep } from './medical';

// Patient - main source for Patient
export * from './patient';

// Check-in & Appointments
export * from './checkin';

// AI & LLM
export * from './llm';
export * from './persona';
export * from './voices';

// Sessions & Knowledge - exclude SessionMetadata (use from patient.ts)
export type {
  SessionStatus,
  EncryptionMetadata,
  ChunkTranscript,
  TranscriptionSources,
  DiarizationMetadata,
  Session,
  SessionDetailResponse,
  SessionsListResponse,
} from './session';
export * from './knowledge';

// Audit
export * from './audit';
