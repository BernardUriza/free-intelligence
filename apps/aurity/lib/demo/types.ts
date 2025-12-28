/**
 * Free Intelligence - Demo Dataset Types
 *
 * Type definitions for deterministic demo datasets.
 *
 * File: lib/demo/types.ts
 * Card: FI-UI-FEAT-207
 * Created: 2025-10-30
 */

/**
 * Demo configuration from environment variables
 */
export interface DemoConfig {
  enabled: boolean;
  seed: string;
  sessions: number; // 12 | 24 | 60
  eventsProfile: 'small' | 'large' | 'mix';
  latencyMs: { min: number; max: number };
  errorRatePct: number; // 0-5
}

/**
 * Demo manifest (trazabilidad)
 */
export interface DemoManifest {
  version: string;
  seed: string;
  sessions: number;
  profile: string;
  latency: string;
  error_rate: number;
  ids_digest: string; // Short hash of all session IDs
  generatedAt: string; // ISO 8601
}

/**
 * Event profile weights for "mix" mode
 */
export interface EventsProfileWeights {
  small: number; // 80% sessions with 30-80 events
  large: number; // 20% sessions with 400-2k events
}

/**
 * Speaker templates for deterministic generation
 */
export interface SpeakerTemplate {
  role: 'doctor' | 'patient' | 'nurse' | 'system';
  name: string;
}

/**
 * Event kind templates
 */
export type EventKind =
  | 'INTERACTION_STARTED'
  | 'INTERACTION_COMPLETED'
  | 'ASR_TRANSCRIBED'
  | 'LLM_RESPONSE_GENERATED'
  | 'DECISION_APPLIED'
  | 'REDACTION_APPLIED'
  | 'POLICY_EVALUATED'
  | 'EXPORT_REQUESTED'
  | 'AUDIT_LOGGED';

/**
 * Text corpus for demo events (medical-style)
 */
export interface TextCorpus {
  symptoms: string[];
  diagnoses: string[];
  treatments: string[];
  questions: string[];
  responses: string[];
}
