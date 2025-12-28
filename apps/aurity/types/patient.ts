/**
 * Patient and Session Types
 *
 * Shared types for patient management and session handling.
 * Used across patient selector, medical workflow, and session management.
 *
 * SOLID: Interface Segregation - Small, focused interfaces
 */

/** Patient demographic and medical information */
export interface Patient {
  id: string;
  name: string;
  age: number;
  gender: 'Masculino' | 'Femenino' | 'Otro';
  medicalHistory?: string[];
  allergies?: string[];
  chronicConditions?: string[];
  currentMedications?: string[];
  // Backend fields for edit operations
  curp?: string | null;
  fechaNacimiento: string; // ISO date string "YYYY-MM-DD"
  createdAt: string;
  updatedAt?: string | null;
}

/** Session metadata from backend */
export interface SessionMetadata {
  session_id: string;
  thread_id: string | null;
  owner_hash: string;
  created_at: string;
  updated_at: string;
}

/** Session timespan information */
export interface SessionTimespan {
  start: string;
  end: string;
  duration_ms: number;
  duration_human: string;
}

/** Session size metrics */
export interface SessionSize {
  interaction_count: number;
  total_tokens: number;
  total_chars: number;
  avg_tokens_per_interaction: number;
  size_human: string;
}

/** Policy compliance badges */
export interface PolicyBadges {
  hash_verified: string;
  policy_compliant: string;
  redaction_applied: string;
  audit_logged: string;
}

/** Task status types */
export type TaskStatus = 'not_started' | 'pending' | 'in_progress' | 'completed' | 'failed';

/** Session task statuses */
export interface SessionTaskStatus {
  soapStatus: TaskStatus;
  diarizationStatus: TaskStatus;
}

/** Complete session summary */
export interface SessionSummary {
  metadata: SessionMetadata;
  timespan: SessionTimespan;
  size: SessionSize;
  policy_badges: PolicyBadges;
  preview: string;
  patient_name?: string;
  doctor_name?: string;
}

/** Session filter options */
export type SessionFilter = 'all' | 'today' | 'week';
